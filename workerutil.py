import os
from novautil import nc
import paramiko
import time
from celeryapp import celery

debug = False
#nc = novautil.getnovaclient()
# TODO: extract local settings. Currently hardcoded settings will not work for all
workerconfig = {
    'image' : nc.images.find(name='G10-Airfoil-snap2').id,
    'flavor' : nc.flavors.find(name='m1.large').id,
    'network' : nc.networks.find(label='ext-net').id,
    'key_name' : 'rymanserverkey'
}
key_filename = 'rymanserverkey.pem'
worker_files = ['celerytasks.py', 'celeryapp.py']
vm_name_prefix = 'RymanAirfoil-worker'
name_count = 0
vms = []

def getworkernamegen():
    return ((worker_name_prefix + str(i)) for i in xrange(n_worker_vms))

def next_vm_name():
    global name_count
    name_count += 1
    return vm_name_prefix + str(name_count)

def create_worker_vm(name=None, kwargs=workerconfig): 
    global nc
    global vms
    if not name:
        name = next_vm_name()
    vm = nc.servers.create(name, **kwargs)
    vms.append(vm)
    return vm

def get_network(vm, netname):
    global nc
    while True:
        nets = nc.servers.ips(vm)
        if netname in nets:
            return nets[netname]

def ssh_exec_check_failure(ssh, command):
    global debug
    (stdin, stdout, stderr) = ssh.exec_command(command)
    if debug:
        first = True
        for part in command.split('\n'):
            if first:
                print '\t>>'+part
                first = False
            else:
                print '\t  '+part
        for line in stdout.readlines():
            print '\t'+line,
    failure = False
    first = True
    for line in stderr.readlines():
        if first:
            print 'Failed to execute command:'
            print command
            first = False
            failure = True
        print '\t'+line,
    return failure

def start_celery_workers_remote(ssh): 
    # broker is assumed to be located on the machine running this function
    failure = False
    with ssh.open_sftp() as sftp:
        print 'Uploading required celery worker files with sftp', sftp
        sftp.put('celeryconfigremote.py', 'celeryconfig.py')
        for file_name in worker_files:
            sftp.put(file_name, file_name)
    envcmd = "env"
    for envvar in ['OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_NAME', 'OS_AUTH_URL']:
        envcmd += " {0}={1}".format(envvar, os.environ[envvar])
    print 'Starting celery worker on remote machine with ssh', ssh
    if ssh_exec_check_failure(ssh, "{0} celery worker --hostname=%h --app=celeryapp:celery --detach".format(envcmd)):
        print 'Failed to start celery workers on remote machine.'
        return False
    return True

def stop_celery_workers_remote(ssh, force=False):
    cmd = "ps auxww | grep 'celery worker' | awk '{print $2}' | xargs kill"
    if force:
        cmd += " -9"
    print 'Stopping celery workers on remote machine with ssh', ssh
    if ssh_exec_check_failure(ssh, cmd):
        print 'Failed to stop celery workers on remote machine.'
        return False
    return True

def get_local_ip(vm):
    return get_network(vm, 'ACC-Course-net')[0]['addr']

def establish_worker_ssh(ssh, ip):
    print 'Establishing ssh connection to VM with ip:', ip
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            ssh.connect(ip, username='ubuntu', key_filename = key_filename, timeout=60)
            break
        except:
            print 'ssh connection failed, trying again in 3 seconds...'
            time.sleep(3)
    print 'ssh connection established successfully'
    return

def spawn_worker_vm(name=None):
    global nc
    print '-= Spawning worker VM =-'
    vm = create_worker_vm(name)
    print 'name:', vm.name
    print 'Waiting for VM network ...'
    vm_ip = get_local_ip(vm)
    print 'ip:' , vm_ip
    failmsg = ''
    with paramiko.SSHClient() as ssh:
        establish_worker_ssh(ssh, vm_ip)
        if not start_celery_workers_remote(ssh):
            failmsg = ', but failed to start celery workers'
    print 'Successfully spawned worker VM'+failmsg
    return vm

def add_worker_vms(n=1):
    for i in xrange(n):
        spawn_worker_vm()
    return

def clear_worker_vms():
    stop_worker_vms()
    global name_count
    name_count = 0
    return

def stop_worker_vms():
    for vm in list_worker_vms():
        stop_worker_vm(vm)
    return

def stop_worker_vm(vm, force=False):
    print '-= Stopping worker VM =-'
    print 'name:', vm.name
    vm_ip = get_local_ip(vm)
    print 'ip:', vm_ip
    stop_celery_workers_on_worker_vm(vm_ip, force)
    print 'Deleting worker vm', vm
    vm.delete()
    return

def stop_celery_workers_on_worker_vm(vm_ip, force=False):
    with paramiko.SSHClient() as ssh:
        establish_worker_ssh(ssh, vm_ip)
        stop_celery_workers_remote(ssh, force)
    return

def kill_worker_vms():
    for vm in list_worker_vms():
        print 'Deleting worker vm', vm
        vm.delete()
    return

def list_worker_vms():
    global nc
    return filter(lambda serv: serv.name.startswith(vm_name_prefix), nc.servers.list())