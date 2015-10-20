To start Celery Worker:
>> celery -A app.celery worker&

To start app:
>> python app.py&

To kill app or celery worker:
>> ps auxww | grep 'celery worker' | awk '{print $2}' | xargs kill
>> ps auxww | grep 'app' | awk '{print $2}' | xargs kill

To run rest api:
>> curl "http://localhost:5000/af?min_angle=10&max_angle=10&speed=10"

for result:
>> curl "http://localhost:5000/af/result/<task_id>"

change your parameters as desired

If you want to turn this into a distributed program:
add a user to rabbitmq server
change all settings.py files to contain IP of rabbitmq server location plus username and pass



