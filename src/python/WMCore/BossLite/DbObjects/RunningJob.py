#!/usr/bin/env python
"""
_RunningJob_

Class for jobs that are running
"""

__version__ = "$Id: RunningJob.py,v 1.7 2010/05/03 20:38:39 spigafi Exp $"
__revision__ = "$Revision: 1.7 $"

# imports
import time
import logging

from WMCore.BossLite.DbObjects.DbObject import DbObject
from WMCore.BossLite.Common.Exceptions import JobError, DbError


class RunningJob(DbObject):
    """
    RunningJob object
    """

    # fields on the object and their names on database
    fields = { 'id' : 'id',
               'jobId' : 'job_id',
               'taskId' : 'task_id',
               'submission' : 'submission',
               'state' : 'state',
               'scheduler' : 'scheduler',
               'service' : 'service',
               'schedulerAttributes' : 'sched_attr',
               'schedulerId' : 'scheduler_id',
               'schedulerParentId' : 'scheduler_parent_id',
               'statusScheduler' : 'status_scheduler',
               'status' : 'status',
               'statusReason' : 'status_reason',
               'destination' : 'destination',
               'lbTimestamp' : 'lb_timestamp',
               'submissionTime' : 'submission_time',
               'scheduledAtSite' : 'scheduled_at_site',
               'startTime' : 'start_time',
               'stopTime' : 'stop_time',
               'stageOutTime' : 'stageout_time',
               'getOutputTime' : 'getoutput_time',
               'outputRequestTime' : 'output_request_time',
               'outputEnqueueTime' : 'output_enqueue_time',
               'getOutputRetry' : 'getoutput_retry',
               'outputDirectory' : 'output_dir',
               'storage' : 'storage',
               'lfn' : 'lfn',
               'applicationReturnCode' : 'application_return_code',
               'wrapperReturnCode' : 'wrapper_return_code',
               'processStatus' : 'process_status',
               'closed' : 'closed'
             }

    # mapping between field names and database fields including superclass
    mapping = fields

    # default values for fields
    defaults = { 'id' : None,
                 'jobId' : None,
                 'taskId' : None,
                 'submission' : None,
                 'state' : None,
                 'scheduler' : None,
                 'service' : None,
                 'schedulerAttributes' : None,
                 'schedulerId' : None,
                 'schedulerParentId' : None,
                 'statusScheduler' : None,
                 'status' : None,
                 'statusReason' : None,
                 'destination' : None,
                 'lbTimestamp' : None,
                 'submissionTime' : None,
                 'scheduledAtSite' : None,
                 'startTime' : None,
                 'stopTime' : None,
                 'stageOutTime' : None,
                 'getOutputTime' : None,
                 'outputRequestTime' : None,
                 'outputEnqueueTime' : None,
                 'getOutputRetry' : 0,
                 'outputDirectory' : None,
                 'storage' : None,
                 'lfn' : '',
                 'applicationReturnCode' : None,
                 'wrapperReturnCode' : None,
                 'processStatus' : None,
                 'closed' : None
               }

    # database properties
    tableName = "bl_runningjob"
    tableIndex = ["taskId", "jobId", "submission"]
    timeFields = ['lbTimestamp', 'submissionTime', 'startTime', \
                  'scheduledAtSite' , 'stopTime', 'stageOutTime', \
                  'outputRequestTime', 'outputEnqueueTime', 'getOutputTime']
    # exception class
    exception = JobError

    ##########################################################################

    def __init__(self, parameters = {}):
        """
        initialize a RunningJob instance
        """

        # call super class init method
        DbObject.__init__(self, parameters)

        # set operational errors
        self.warnings = []
        self.errors = []

        # flag for scheduler interaction
        self.active = True
        self.existsInDataBase = False

    ##########################################################################

    def exists(self, db, noDB = False):
        """
        Am I in the database?
        """

        if noDB:
            if self.data['id'] > 0:
                return self.data['id']
            else:
                return False
        else:
            tmpId = db.objExists(self)
                        
            if tmpId:
                self.data['id'] = tmpId
            
            return tmpId

    ##########################################################################

    def create(self, db):
        """
        Create a new Running Job
        """

        db.objCreate(self)
        
        # update ID & check... necessary call!
        if self.exists(db) : 
            self.existsInDataBase = True

    ##########################################################################

    def save(self, db):
        """
        Save the job
        """

        if not self.existsInDataBase:
            self.create(db)
        else:
            db.objSave(self)               

        self.existsInDataBase = True
        return

    ##########################################################################

    def load(self, db, deep = True):
        """
        Load from the database
        """
        
        result = db.objLoad(self)
        
        if result == []:
            # Then the job did not exist
            # no exception will raise?
            
            # is this message useful? TEMPORARY SUPPRESSED
            #logging.error(
            # "Attempted to load non-existant runningJob with parameters:\n %s" 
            #            % (self.data) )
            return 
        
        self.data.update(result[0])
        
        # consistency?
        self.existsInDataBase = True
        
        return 

    ##########################################################################

    def remove(self, db):
        """
        remove job object from database
        """
        
        if not self.existsInDataBase:
            logging.error("Cannot remove from DB non-existant runningJob %s" 
                          % (self.data) )
            return 0
        
        db.objRemove(self) 
        
        # update status
        self.existsInDataBase = False

        # return number of entries removed
        return 1

    ##########################################################################

    def isError(self):
        """
        returns the status based on the self.errors list
        """

        return ( len( self.errors ) != 0 )
        
    ##########################################################################

    def update(self, db, deep = True):
        """
        update job information in database
        """

        return self.save(db, deep)
