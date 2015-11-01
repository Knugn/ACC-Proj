from __future__ import absolute_import
from os import path, environ
import json
from flask import Flask, Blueprint, abort, jsonify, request, session
import settings
from celery import Celery
import urllib2
from pprint import pprint
import subprocess
import uuid
import os
import re

app = Flask(__name__)
app.config.from_object(settings)

task_ids = []
task_dict = {}

def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

@celery.task(name="tasks.airfoil")
def airfoil(angle, n_nodes, n_levels, num_samples, visc, speed, T, job_id):
        print "working on angle " +str(angle)
        #static variables needed for gmsh/airfoil
        n_angles = 1
        #n_nodes = 200
        #n_levels = 0
        #num_samples = 10
        #visc = 0.0001
        #T = 1

        lift_values = []
        origWD = os.getcwd()
        #anglediff=$((($angle_stop-$angle_start)/$n_angles))

        subprocess.call(['/home/ubuntu/naca_airfoil/run.sh', str(angle),
        str(angle), str(n_angles), str(n_nodes), str(n_levels)])
        filename_msh = "r"+str(n_levels)+"a"+str(angle)+"n"+str(n_nodes)+".msh"
        filename_xml = "r"+str(n_levels)+"a"+str(angle)+"n"+str(n_nodes)+".xml"
        print "before changed dir"
        #changing directories so that when airfoil is run
        #The results are placed in a unique folder (jod_id/angle/)
        os.makedirs(job_id+"/"+str(angle))
        os.chdir(job_id+"/"+str(angle)+"/")
        print "changed dir"
        subprocess.call(['dolfin-convert', '../../msh/'+str(filename_msh), str(filename_xml)])
        print "converted dolfin to xml"
        subprocess.call(['../../navier_stokes_solver/airfoil',
            	str(num_samples), str(visc), str(speed)+".", str(T), filename_xml])
        print "ran airfoil"
        with open('results/drag_ligt.m') as f:
        		for line in f:
        			if not line.startswith("%"):
        				values = line.split()
        				lift_values.append(float(values[2]))
        os.chdir(origWD)
        liftval_size = len(lift_values)
        liftval_sum = sum(lift_values)
        liftforce_mean = liftval_sum/liftval_size
	return {'liftforce_mean':liftforce_mean, 'speed':speed, 'angle': angle, 'job_id': job_id}

@app.route("/af")
def run_airfoil(min_angle=10, max_angle=20, n_angles=1, n_nodes=200, n_levels=0, num_samples=10, visc=0.0001, speed=10, T=1):
   global task_dict
   task_ids = []
   min_angle = int(request.args.get("min_angle", min_angle))
   max_angle = int(request.args.get("max_angle", max_angle))
   n_angles=int(request.args.get("n_angles", n_angles))
   n_nodes=int(request.args.get("n_nodes", n_nodes))
   n_levels=int(request.args.get("n_levels", n_levels))
   num_samples=int(request.args.get("num_samples", num_samples))
   visc=float(request.args.get("visc", visc))
   speed=int(request.args.get("speed", speed))
   T=int(request.args.get("T", T))
   
   job_id = str(uuid.uuid4())
   os.makedirs(job_id)
   anglediff=(((max_angle-min_angle)/n_angles))
   if anglediff < 1:
      anglediff = 1
   for angle in xrange(min_angle, (max_angle+1), int(anglediff)):
	   res=airfoil.apply_async((angle, n_nodes, n_levels, num_samples, visc, speed, T, job_id))
	   task_ids.append(res.task_id)
   task_dict[job_id] = task_ids
   return jsonify(job_id=job_id, minimum_angle=min_angle, maximum_angle=max_angle)

@app.route("/af/result/<job_id>")
def show_result_airfoil(job_id):
       global task_dict
       retvals = []
       for task_id in task_dict[job_id]:
               job_result = airfoil.AsyncResult(task_id).get(timeout=1000000000.0)               
               print job_result
               ret = {'mean_liftforce':job_result['liftforce_mean'],
               'speed':job_result['speed'],
               'angle':job_result['angle'],
	       'task_id': task_id}

               retvals.append(ret)
       return jsonify(retvals=retvals)


from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)


@app.route('/index')
def index():
	return render_template('index.html')


if __name__ == "__main__":
    port = int(environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)



