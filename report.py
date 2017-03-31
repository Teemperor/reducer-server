#!/bin/python
import re
import os
import hurry.filesize
import json
import time
import subprocess
import shutil

upload_dir = "/var/reducing/uploads"
data_dir = "/var/reducing/data"
output_dir = "/var/www/out"
run_dir = "/home/reduce_slave/"
reduce_user = "reduce_slave"
log_dir = "/var/www/logs/"
delete_dir = "/var/reducing/delete"

pattern = re.compile("([0-9]+\\.[0-9]*) %, ([\\.0-9]+) bytes\\)")

def is_pid_alive(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

class UploadJob:
    def __init__(self, path):
        self.upload_path = path
        self.filename = os.path.basename(path)
        self.name = self.filename
        self.data_path = os.path.join(data_dir, self.filename)
        self.output_path = os.path.join(output_dir, self.filename)
        self.running_file = self.data_path + ".running"
        self.running = False
        self.update()

        self.job_process = None
        if not self.job_done:
            self.new_size = 0
            self.new_size_str = "NONE"
        else:
            self.new_size = os.stat(self.output_path).st_size
            self.new_size_str = hurry.filesize.size(self.new_size)

        self.orig_size = os.stat(path).st_size
        self.orig_size_str = hurry.filesize.size(self.orig_size)

        self.progress = 20.0

    def update(self):
        self.job_done = os.path.isfile(self.output_path)

    def start(self):
        print("Running " + self.name)
        assert(self.job_done == False)
        assert(self.running == False)
        touch_file = open(self.running_file, "w")
        touch_file.close()
        self.running = True
        self.job_process = subprocess.Popen(["sudo", "-u", reduce_user, "bash",
             "/var/reducing/data/run.sh", self.upload_path])
        self.job_process.poll()
        time.sleep(0.5)

    def remove(self):
        try:
            os.remove(self.upload_path)
        except OSError:
            pass
        try:
            os.remove(self.output_path)
        except OSError:
            pass

    def is_alive(self):
        assert(self.running == True)
        self.job_process.poll()
        return self.job_process.returncode == None
#        try:
#            assert(self.running == True)
#            pid_file = open(run_dir + ".pid")
#            pid = pid_file.read().strip()
#            pid_file.close()
#            is_pid_alive(int(pid))
#        except FileNotFoundError as e:
#            print("Couldn't open PID file")


    def try_stop(self):
        if self.is_alive():
            return False
        else:
            self.running = False
            #self.job_process.wait()
            os.remove(self.running_file)
            subprocess.call(["sudo", "-u", reduce_user, "bash",
                      "/var/reducing/data/pkg.sh", run_dir + "/result.zip"])
            shutil.move(run_dir + "/result.zip", self.output_path)
            print("Stopped " + self.name)
            return True

    def get_log(self):
        assert(self.running == True)
        try:
            log_file = open(run_dir + "/.log")
            lines = log_file.readlines()
            log_file.close()
            return lines
        except FileNotFoundError as e:
            return ["No log yet"]

class JobList:
    def __init__(self):
        self.jobs = []
        self.update()

    def update(self):
        to_delete = [f for f in os.listdir(delete_dir) if os.path.isfile(os.path.join(delete_dir, f))]

        for f in to_delete:
            for job in self.jobs:
                if job.filename == f:
                    job.remove()
                    self.jobs.remove(job)
                    break
            os.remove(os.path.join(delete_dir, f))

        uploads = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))]
        for job in self.jobs:
            job.update()

        for file in uploads:
            file = os.path.join(upload_dir, file)
            already_queued = False
            for job in self.jobs:
                if job.upload_path == file:
                    already_queued = True
            if not already_queued:
                self.jobs.append(UploadJob(file))
        # sort by shorted job first
        self.jobs.sort(key=lambda x: x.orig_size)

def status_from_log(lines):
    for line in reversed(lines):
        m = re.search(pattern, line)
        if m:
            return float(m.group(1))
            break
    return None

def get_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            if f == ".log":
                continue
            if f == ".pid":
                continue
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def generate_job_report(job, out):
    out.write('<div class="job_div">')
    out.write("  <h3>" + job.name)
    if job.running:
        out.write(' <i class="fa fa-cog fa-spin"></i>')
    out.write("</h3>\n")
    if job.running:
        out.write('<p class="size_str">Size: ' + hurry.filesize.size(get_size(run_dir)) + '</p>')
        lines = job.get_log()
        reduction = status_from_log(lines)
        if reduction == None:
            out.write('  <progress></progress>\n')
        else:
            out.write('  <progress value="' + str(reduction) + '" max="100"></progress>\n')
        out.write("  <p>Output:</p>\n")
        out.write("  <pre>\n")
        if len(lines) > 30:
            lines = lines[-30:]

        for line in lines:
            out.write(line)

        out.write("  </pre>\n")
    else:
        out.write('<p class="size_str">Size: ' + job.orig_size_str + '</p>\n')
    if job.job_done:
        out.write('<a href="out/' + job.filename + '">Download result</a>\n')
    if not job.running:
        out.write('<a href="delete.php?file=' + job.filename + '">Remove job</a>\n')

    out.write("</div>\n")

def generate_status(out):
    out.write("""
<!DOCTYPE html>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"><html>
<head>
  <link rel="stylesheet" type="text/css" href="theme.css">
  <script src="jquery-3.2.0.min.js"></script>  <script>
$(function() {
    startRefresh();
});

oldData = ""

function startRefresh() {
    setTimeout(startRefresh,400);
    $.get('content.html', function(data) {
        if (oldData !== data) {
            oldData = data;
            console.log(data);
            $('#main').html(data);
        }
    });
}

</script></head>
<body>
<form action="upload.php" method="post" enctype="multipart/form-data">
    Select zip file that contains a new job (top-level test.sh file):
    <input type="file" name="fileToUpload" id="fileToUpload">
    <input type="submit" value="Start job" name="submit">
</form>

  <div id="main">
  <h1> Loading... <h2>
  <progress></progress>
  </div>
</body>
</html>
""")

def generate_report(jobs, out):
    out.write("<h2>Running job</h2>\n")
    for job in jobs:
        if job.running:
            generate_job_report(job, out)
    out.write("<h2>Queued jobs</h2>\n")
    for job in jobs:
        if not job.job_done:
            if not job.running:
                generate_job_report(job, out)
    out.write("<h2>Finished jobs</h2>\n")
    for job in jobs:
        if job.job_done:
            generate_job_report(job, out)

job_list = JobList()

status = open("status.html", "w")
generate_status(status)
status.close()

while True:
    job_list.update()
    a_job_running = False
    for job in job_list.jobs:
        if job.job_done:
            continue
        if job.running:
            a_job_running = True
            job.try_stop()
            break

    if not a_job_running:
        for job in job_list.jobs:
            if job.job_done:
                continue
            if not job.running:
                job.start()
                break

    report = open("content.html", "w")
    generate_report(job_list.jobs, report)
    report.close()

    time.sleep(1)
