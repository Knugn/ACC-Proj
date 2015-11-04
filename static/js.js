$('document').ready(function() {
    'use strict';


    function launchJob(min_angle, max_angle, n_angles, n_nodes, n_levels, num_samples, visc, speed, time) {
        var ip = location.host;
        var url = 'http://' + ip +'/af?' +
        'min_angle=' + min_angle +
        '&max_angle=' + max_angle +
        '&n_angles=' + n_angles +
        '&n_nodes=' + n_nodes +
        '&n_levels=' + n_levels +
        '&num_samples=' + num_samples +
        '&visc=' + visc +
        '&speed=' + speed +
        '&T=' + time
        ;

        $.when(
            $.ajax({
                url: url
            })
        ).then(jobInfo);
    }

    function checkJob(jobId) {
        var ip = location.host;
        $.when(
            $.ajax({
                url: 'http://'+ip+'/af/result/' + jobId
            })
        ).then(jobResult);
    }

    function jobInfo(info) {
        console.log('jobinfo'  + JSON.stringify(info));
        var jobId = info.job_id;
        console.log('jobid: ' +jobId);

        $('#output').val('Running job ' + jobId);

        checkJob(jobId);
    }

    function jobResult(result) {
        console.log('jobresult '  + JSON.stringify(result));
        var textInOutput = $('#output').val();
        var result = result.job_result
        var outputText = textInOutput;
        outputText += '\nAngle \tDrag         \tLift\n';
        
            for(var i = 0; i < result.length; i++) {
                var angle = result[i].angle;
                var mean_dragforce = result[i].dragforce_mean;
                var mean_liftforce = result[i].liftforce_mean;
                mean_dragforce = Number((mean_dragforce).toFixed(3));
                mean_liftforce = Number((mean_liftforce).toFixed(3));
                outputText += angle + '       \t' + mean_dragforce + '   \t' + mean_liftforce + '\n'
                    //'\nAngle ' + angle + ':\n'
                    //+ '\tMean drag force: '+ mean_dragforce,
                    //+ '\tMean lift force: '+ mean_liftforce;
            }
        console.log('output text:' + outputText);
        $('#output').val(outputText);
    }

    function validInput(inputs) {
        for (var i = 0; i < inputs.length; i++) { 
            if(inputs[i] === '') {
                return false;
            }
        }
        return true;
    }

    $('#output').val('');

    $("#button").click( function()
    {
        var min_angle = $('#min_angle').val();
        var max_angle = $('#max_angle').val();
        var n_angles = $('#n_angles').val();
        var n_nodes = $('#n_nodes').val();
        var n_levels = $('#n_levels').val();
        var num_samples = $('#num_samples').val();
        var visc = $('#visc').val();
        var speed = $('#speed').val();
        var time = $('#time').val();

        var inputs = [min_angle, max_angle, n_angles, n_nodes, n_levels, num_samples, visc, speed, time];

        if (!validInput(inputs)) {
            alert("Please fill in all fields");
        }
        else {
            launchJob(min_angle, max_angle, n_angles, n_nodes, n_levels, num_samples, visc, speed, time);
        }
    });

});

function isNumberKey(evt){
    var charCode = (evt.which) ? evt.which : event.keyCode
    if (charCode > 31 && (charCode < 48 || charCode > 57))
        return false;
    return true;
}

