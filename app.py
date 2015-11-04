from __future__ import absolute_import
from os import path, environ
import json
from flask import Flask, Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
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

origwd = os.getcwd()

run_sh_path = os.path.abspath('./run.sh')
airfoil_path = os.path.abspath('./airfoil')
local_data_path = os.path.abspath('./local/data/')
local_geo_path = os.path.join(local_data_path,'geo/')
local_msh_path = os.path.join(local_data_path,'msh/')
local_xml_path = os.path.join(local_data_path,'xml/')
local_results_path = os.path.join(local_data_path,'results/')

default_min_angle=10
default_max_angle=20
default_n_angles=1
default_n_nodes=200
default_n_levels=0
default_num_samples=10
default_visc=0.0001
default_speed=10
default_T=1

task_ids = []
job_tasks_dict = {}
job_input_dict = {}

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
    print "Working on angle " + str(angle) + " ..."
    n_angles = 1

    curwd = os.getcwd()
    if curwd != origwd:
        os.chdir(origwd)

    fileutil.mkdir_ifnexists(local_data_path)
    fileutil.mkdir_ifnexists(local_geo_path)
    fileutil.mkdir_ifnexists(local_msh_path)
    fileutil.mkdir_ifnexists(local_xml_path)
    fileutil.mkdir_ifnexists(local_results_path)
    
    subprocess.call([run_sh_path, str(angle), str(angle), str(n_angles), str(n_nodes), str(n_levels)])
    
    filename_format = 'r{0}a{1}n{2}'.format(n_levels, angle, n_nodes)+'{0}'    
    msh_file_path = os.path.join(local_msh_path, filename_format.format('.msh'))
    xml_file_path = os.path.join(local_xml_path, filename_format.format('.xml'))
    print "Converting from Gmsh format (.msh) to DOLFIN XML format (.xml) ..."
    subprocess.call(['dolfin-convert', msh_file_path, xml_file_path])
    
    #print "before changed dir"
    result_dir_name = filename_format.format('_samp{0}visc{1}speed{2}time{3}'.format(num_samples, visc, speed, T)).replace(".", "-")
    airfoil_exec_path = os.path.join(local_results_path, result_dir_name)
    fileutil.mkdir_ifnexists(airfoil_exec_path)
    airfoil_log_path = os.path.join(airfoil_exec_path, 'log.txt')
    
    #print 'Changing working directory to: ' + airfoil_exec_path
    #os.chdir(airfoil_exec_path)
    #print "changed dir"
    
    print 'Running airfoil simulation ...'
    with open(airfoil_log_path, 'w') as log:
        subprocess.call([airfoil_path, str(num_samples), str(visc), str(speed), str(T), xml_file_path], 
                        stdout=log, cwd=airfoil_exec_path)
    #print "ran airfoil"
    lift_values = []
    drag_values = []
    drag_lift_path = os.path.join(airfoil_exec_path, 'results', 'drag_ligt.m')
    print 'Reading results from: ' + drag_lift_path
    with open(drag_lift_path, 'r') as f:
        for line in f:
            if not line.startswith("%"):
                values = line.split()
                lift_values.append(float(values[1]))
                drag_values.append(float(values[2]))
    
    #print 'Restoring working directory to: ' + origwd
    #os.chdir(origwd)
    
    liftforce_mean = sum(lift_values)/len(lift_values)
    dragforce_mean = sum(drag_values)/len(drag_values)
    return {'angle':angle, 
            'liftforce_vector':lift_values, 'dragforce_vector':drag_values,
            'liftforce_mean':liftforce_mean, 'dragforce_mean':dragforce_mean}
            #, 'speed':speed}
    

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
    job_input_dict[job_id] = {
        'NACA':'0012',
        'n_nodes':n_nodes,
        'n_levels':n_levels,
        'num_samples':num_samples,
        'visc':visc,
        'speed':speed,
        'T':T
        }
    
    anglediff=(((max_angle-min_angle)/n_angles))
    if anglediff < 1:
        anglediff = 1
    for angle in xrange(min_angle, (max_angle+1), int(anglediff)):
        res=airfoil.apply_async((angle, n_nodes, n_levels, num_samples, visc, speed, T, job_id))
        task_ids.append(res.task_id)
    job_tasks_dict[job_id] = task_ids
    return jsonify(job_id=job_id, minimum_angle=min_angle, maximum_angle=max_angle)

@app.route("/af/result/<job_id>")
def show_result_airfoil(job_id):
    global task_dict
    #retvals = []
    job_result = []
    for task_id in job_tasks_dict[job_id]:
        task_result = airfoil.AsyncResult(task_id).get(timeout=1000000000.0)
        #angle = task_result['angle']
        #del task_result['angle']
        #job_result[angle] = task_result
        job_result.append(task_result)
        #print job_result
        #ret = {'mean_liftforce':job_result['liftforce_mean'],
        #       'speed':job_result['speed'],
        #       'angle':job_result['angle'],
        #       'task_id': task_id}
        #retvals.append(ret)
    ret = {
        'job_id':job_id,
        'job_input':job_input_dict[job_id],
        'job_result':job_result
          }
    del job_tasks_dict[job_id]
    del job_input_dict[job_id]
    return jsonify(ret)
    #return jsonify(retvals=retvals)

#from flask import (
#    Flask,
#    abort,
#    flash,
#    redirect,
#    render_template,
#    request,
#    url_for,
#)

@app.route('/index')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    port = int(environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
