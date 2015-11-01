from __future__ import absolute_import
from os import path, environ
import json
from flask import Flask, Blueprint, abort, jsonify, request, session, url_for, redirect
import settings
from celery import Celery
import urllib2
from pprint import pprint
import subprocess
import sys
import uuid
import os
import re
import fileutil

app = Flask(__name__)
app.config.from_object(settings)

airfoil_path = os.path.abspath('./airfoil')
local_data_path = os.path.abspath('./local/data/')
local_geo_path = os.path.join(local_data_path,'geo/')
local_msh_path = os.path.join(local_data_path,'msh/')
local_xml_path = os.path.join(local_data_path,'xml/')
local_results_path = os.path.join(local_data_path,'results/')

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
def airfoil(angle, speed, job_id):
    print "working on angle "+str(angle)
    #static variables needed for gmsh/airfoil
    n_angles = 1
    n_nodes = 200
    n_levels = 0
    num_samples = 10
    visc = 0.0001
    T = 1
    
    origWD = os.getcwd()
    
    fileutil.mkdir_ifnexists(local_data_path)
    fileutil.mkdir_ifnexists(local_geo_path)
    fileutil.mkdir_ifnexists(local_msh_path)
    fileutil.mkdir_ifnexists(local_xml_path)
    fileutil.mkdir_ifnexists(local_results_path)
    
    #for angle in xrange(min_angle, (max_angle+1)):
    filename_format = 'r{0}a{1}n{2}'.format(n_levels, angle, n_nodes)+'{0}'
    subprocess.call(['./run.sh', str(angle), str(angle), str(n_angles), str(n_nodes), str(n_levels)])
    #filename_msh = "r"+str(n_levels)+"a"+str(angle)+"n"+str(n_nodes)+".msh"
    #filename_xml = "r"+str(n_levels)+"a"+str(angle)+"n"+str(n_nodes)+".xml"
    msh_file_path = os.path.join(local_msh_path, filename_format.format('.msh'))
    xml_file_path = os.path.join(local_xml_path, filename_format.format('.xml'))
    subprocess.call(['dolfin-convert', msh_file_path, xml_file_path])
    print "converted dolfin to xml"
    
    print "before changed dir"
    #changing directories so that when airfoil is run
    #The results are placed in a unique folder (jod_id/angle/)
    #os.makedirs(job_id+"/"+str(angle))
    #os.chdir(job_id+"/"+str(angle)+"/")
    result_dir_name = filename_format.format('_samp{0}visc{1}speed{2}time{3}'.format(num_samples, visc, speed, T)).replace(".", "-")
    airfoil_exec_path = os.path.join(local_results_path, result_dir_name)
    fileutil.mkdir_ifnexists(airfoil_exec_path)
    os.chdir(airfoil_exec_path)
    print "changed dir"
    with open('log.txt', 'w') as log:
        subprocess.call([airfoil_path, str(num_samples), str(visc), str(speed), str(T), xml_file_path], stdout=log)
    print "ran airfoil"
    lift_values = []
    drag_values = []
    with open('results/drag_ligt.m') as f:
        for line in f:
            if not line.startswith("%"):
                values = line.split()
                lift_values.append(float(values[1]))
                drag_values.append(float(values[2]))
    os.chdir(origWD)
    
    #liftval_size = len(lift_values)
    #liftval_sum = sum(lift_values)
    liftforce_mean = sum(lift_values)/len(lift_values)
    dragforce_mean = sum(drag_values)/len(drag_values)
    return {'angle':angle, 'liftforce_mean':liftforce_mean, 'dragforce_mean':dragforce_mean, 'speed':speed}

@app.route("/af")
def run_airfoil(min_angle=10, max_angle=20, speed=10):
    global task_dict
    task_ids = []
    min_angle = int(request.args.get("min_angle", min_angle))
    max_angle = int(request.args.get("max_angle", max_angle))
    speed = int(request.args.get("speed", speed))
    job_id = str(uuid.uuid4())
    #os.makedirs(job_id)
    for angle in xrange(min_angle, (max_angle+1)):
        res=airfoil.apply_async((angle, speed, job_id))
        task_ids.append(res.task_id)
    task_dict[job_id] = task_ids
    return redirect(url_for('show_result_airfoil', job_id=job_id))
    #return jsonify(job_id=job_id, minimum_angle=min_angle, maximum_angle=max_angle, result_url=url_for('show_result_airfoil', job_id=job_id))

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

if __name__ == "__main__":
    port = int(environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
