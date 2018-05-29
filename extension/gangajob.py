from __future__ import print_function
import re
from IPython.utils.io import capture_output
import time

ganga_imported = False
with capture_output() as ganga_import_output:
    try:
        import ganga.ganga
        ganga_imported = True
    except ImportError as e:
        print("GangaMonitor: Unable to import Ganga in Python \n %s \n" % str(e))

if ganga_imported:
    print("GangaMonitor: Ganga Imported succesfully")

class GangaMonitor:
    def __init__(self, ipython):
        self.ipython = ipython
    
    def __handle_incoming_msg(self, msg):
        print("Message recieved from frontend: \n %s \n" % str(msg))

    def register_comm(self):
        self.ipython.kernel.comm_manager.register_target("GangaMonitor", self.comm_target)
    
    def comm_target(self, comm, msg):
        print("Comm Opened: \n %s \n" % str(msg))
        self.comm = comm

        @self.comm.on_msg
        def _recv(msg):
            self.__handle_incoming_msg(msg)
        self.comm.send({"msgtype": "commopen"})

    def send(self, msg):
        self.comm.send(msg)

    def extract_job_obj(self, code): # Handle not found error
        regex = r"(\w+)\s*=\s*ganga.Job\(\)"
        matches = re.finditer(regex, code, re.MULTILINE)

        for match in matches:
            obj_name = match.group(1)
        
        return str(obj_name)

    def run(self, raw_cell):
        job_obj_name = self.extract_job_obj(raw_cell)
        mirror_code = "job_obj = %s" % job_obj_name

        try:
            with capture_output() as ganga_job_output:
                exec(raw_cell)
                ganga.runMonitoring()
                print("Monitoring ON")
        except Exception as e:
            print("GangaMonitor: %s" % str(e))
        else:
            exec(mirror_code)
            job_info = {
                "msgtype": "jobinfo",
                "id": job_obj.id,
                "name": str(job_obj.name),
                "backend": str(job_obj.backend.__class__.__name__),
                "subjobs": len(job_obj.subjobs),
                "status": "submitted",
                "job_submission_time": str(job_obj.time.submitting())
            }
            self.send(job_info)
            while True:
                job_status = {
                    "msgtype": "jobstatus",
                    "id": job_obj.id,
                    "status": str(job_obj.status),
                    "duration": str(job_obj.time.runtime())
                }
                self.send(job_status)
                if (job_status["status"] == "completed"):
                    break
                time.sleep(10)
