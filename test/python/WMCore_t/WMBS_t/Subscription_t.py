#!/usr/bin/env python
#pylint: disable-msg=E1103, W0142, R0201
# E1103: allow thread to hold variables
# W0142: Some people like ** magic
# R0201: Test methods CANNOT be functions

__revision__ = "$Id: Subscription_t.py,v 1.57 2010/05/24 15:40:05 mnorman Exp $"
__version__ = "$Revision: 1.57 $"


import unittest
import logging
import random
import threading

from WMCore.DAOFactory import DAOFactory
from WMCore.WMBS.File import File
from WMCore.WMBS.Fileset import Fileset
from WMCore.WMBS.Workflow import Workflow
from WMCore.WMBS.Subscription import Subscription
from WMQuality.TestInit import TestInit
from WMCore.DataStructs.Run import Run
from WMCore.WMBS.Job      import Job
from WMCore.WMBS.JobGroup import JobGroup
from WMCore.JobStateMachine.ChangeState import ChangeState
from WMCore.JobStateMachine import DefaultConfig

class SubscriptionTest(unittest.TestCase):
    """
    The unittest for the Subscription object

    """
    
    def setUp(self):
        """
        _setUp_

        Setup the database and logging connection.  Try to create all of the
        WMBS tables.  Also, create some dummy locations.
        """
        self.testInit = TestInit(__file__)
        self.testInit.setLogging()
        self.testInit.setDatabaseConnection()
        #self.testInit.clearDatabase(modules = ["WMCore.WMBS"])
        self.testInit.setSchema(customModules = ["WMCore.WMBS"],
                                useDefault = False)

        myThread = threading.currentThread()
        self.daofactory = DAOFactory(package = "WMCore.WMBS",
                                     logger = myThread.logger,
                                     dbinterface = myThread.dbi)
        
        locationAction = self.daofactory(classname = "Locations.New")
        locationAction.execute(siteName = "site1", seName = "goodse.cern.ch")
        locationAction.execute(siteName = "site2", seName = "testse.cern.ch")
        locationAction.execute(siteName = "site3", seName = "badse.cern.ch")
        
        return

    def tearDown(self):
        """
        _tearDown_
        
        Drop all the WMBS tables.
        """
        self.testInit.clearDatabase()
            
    def createSubscriptionWithFileABC(self):
        """
        _createSubscriptionWithFileABC_

        Create a subscription where the input fileset has three files.  Also
        create a second subscription that has acquired two of the files.
        """
        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task = "Test")
        testWorkflow.create()
        testWorkflow2 = Workflow(spec = "specBOGUS.xml", owner = "Simon",
                                name = "wfBOGUS", task = "Test")
        testWorkflow2.create()        

        testFileA = File(lfn = "/this/is/a/lfnA", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileA.addRun(Run(1, *[45]))
                                 
        testFileB = File(lfn = "/this/is/a/lfnB", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))                         
        testFileB.addRun(Run(1, *[45]))
        
        testFileC = File(lfn = "/this/is/a/lfnC", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileC.addRun(Run(2, *[48]))
         
        testFileA.create()
        testFileB.create()
        testFileC.create()
        
        testFileset = Fileset(name = "TestFileset")
        testFileset.create()
        
        testFileset.addFile(testFileA)
        testFileset.addFile(testFileB)
        testFileset.addFile(testFileC)
        testFileset.commit()

        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription2 = Subscription(fileset = testFileset,
                                         workflow = testWorkflow2)
        testSubscription2.create()
        testSubscription2.acquireFiles([testFileA, testFileB])
        
        return (testSubscription, testFileset, testWorkflow, testFileA,
                testFileB, testFileC)

    def testCreateDeleteExists(self):
        """
        _testCreateDeleteExists_

        Create and delete a subscription and use the exists() method to
        determine if the create()/delete() methods were successful.
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()

        assert testSubscription.exists() == False, \
               "ERROR: Subscription exists before it was created"

        testSubscription.create()

        assert testSubscription.exists() >= 0, \
               "ERROR: Subscription does not exist after it was created"

        testSubscription.delete()

        assert testSubscription.exists() == False, \
               "ERROR: Subscription exists after it was deleted"

        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        testWorkflow.delete()        
        return

    def testCreateTransaction(self):
        """
        _testCreateTransaction_

        Create a subscription and commit it to the database.  Rollback the
        database connection and verify that the subscription is no longer
        there.
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()

        assert testSubscription.exists() == False, \
               "ERROR: Subscription exists before it was created"

        myThread = threading.currentThread()
        myThread.transaction.begin()

        testSubscription.create()

        assert testSubscription.exists() >= 0, \
               "ERROR: Subscription does not exist after it was created"

        myThread.transaction.rollback()

        assert testSubscription.exists() == False, \
               "ERROR: Subscription exists after transaction was rolled back."

        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        testWorkflow.delete()        
        return    

    def testDeleteTransaction(self):
        """
        _testDeleteTransaction_

        Create a subscription and commit it to the database.  Begin a new
        transactions and delete the subscription.  Verify that the subscription
        is no longer in the database and then roll back the transaction.  Verify
        that the subscription is once again in the database.
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()

        assert testSubscription.exists() == False, \
               "ERROR: Subscription exists before it was created"

        testSubscription.create()

        assert testSubscription.exists() >= 0, \
               "ERROR: Subscription does not exist after it was created"

        myThread = threading.currentThread()
        myThread.transaction.begin()

        testSubscription.delete()

        assert testSubscription.exists() == False, \
               "ERROR: Subscription exists after it was deleted"

        myThread.transaction.rollback()

        assert testSubscription.exists() >= 0, \
               "ERROR: Subscription does not exist after roll back."

        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        testWorkflow.delete()        
        return
    
    def testFailFiles(self):
        """
        _testFailFiles_

        Create a subscription and fail a couple of files in it's fileset.  Test
        to make sure that only the failed files are marked as failed.
        """
        
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
                  
        testSubscription.create()

        dummyWorkflow = Workflow(spec = "spec1.xml", owner = "Simon",
                                name = "wf002", task='Test')
        dummyWorkflow.create()        

        failSubscription = Subscription(fileset = testFileset,
                                        workflow = dummyWorkflow)
        failSubscription.create()        
        failSubscription.failFiles(failSubscription.filesOfStatus("Available"))

        testSubscription.failFiles([testFileA, testFileC])
        failedFiles = testSubscription.filesOfStatus(status = "Failed")

        goldenFiles = [testFileA, testFileC]
        for failedFile in failedFiles:
            assert failedFile in goldenFiles, \
                   "ERROR: Unknown failed files"
            goldenFiles.remove(failedFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Missing failed files"

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        return

    def testFailFilesTransaction(self):
        """
        _testFailFilesTransaction_

        Create a subscription and fail some files that are in it's input
        fileset.  Rollback the subscription and verify that the files are
        no longer failed.
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
         
        testSubscription.create()

        myThread = threading.currentThread()
        myThread.transaction.begin()

        testSubscription.failFiles([testFileA, testFileC])
        failedFiles = testSubscription.filesOfStatus(status = "Failed")

        goldenFiles = [testFileA, testFileC]
        for failedFile in failedFiles:
            assert failedFile in goldenFiles, \
                   "ERROR: Unknown failed files"
            goldenFiles.remove(failedFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Missing failed files"

        myThread.transaction.rollback()

        failedFiles = testSubscription.filesOfStatus(status = "Failed")

        assert len(failedFiles) == 0, \
               "ERROR: Transaction did not roll back failed files"

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        return    
    
    def testCompleteFiles(self):
        """
        _testCompleteFiles_

        Create a subscription and complete a couple of files in it's fileset.  Test
        to make sure that only the completed files are marked as complete.
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()

        testSubscription.create()
 
        dummyWorkflow = Workflow(spec = "spec2.xml", owner = "Simon",
                                name = "wf003", task='Test')
        dummyWorkflow.create()      

        completeSubscription = Subscription(fileset = testFileset,
                                            workflow = dummyWorkflow)
        completeSubscription.create()
        completeSubscription.completeFiles(completeSubscription.filesOfStatus("Available"))

        testSubscription.completeFiles([testFileA, testFileC])
        completedFiles = testSubscription.filesOfStatus(status = "Completed")

        goldenFiles = [testFileA, testFileC]
        for completedFile in completedFiles:
            assert completedFile in goldenFiles, \
                   "ERROR: Unknown completed file"
            goldenFiles.remove(completedFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Missing completed files"

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()        
        return

    def testCompleteFilesTransaction(self):
        """
        _testCompleteFilesTransaction_

        Create a subscription and complete some files that are in it's input
        fileset.  Rollback the transaction and verify that the files are no
        longer marked as complete.
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
         
        testSubscription.create()

        myThread = threading.currentThread()
        myThread.transaction.begin()
        
        testSubscription.completeFiles([testFileA, testFileC])
        completedFiles = testSubscription.filesOfStatus(status = "Completed")

        goldenFiles = [testFileA, testFileC]
        for completedFile in completedFiles:
            assert completedFile in goldenFiles, \
                   "ERROR: Unknown completed file"
            goldenFiles.remove(completedFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Missing completed files"

        myThread.transaction.rollback()

        completedFiles = testSubscription.filesOfStatus(status = "Completed")

        assert len(completedFiles) == 0, \
               "ERROR: Transaction didn't roll back completed files."

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()        
        return    
    
    def testAcquireFiles(self):
        """
        _testAcquireFiles_

        Create a subscription and acquire a couple of files in it's fileset.  Test
        to make sure that only the acquired files are marked as acquired.
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
         
        testSubscription.create()
        
        dummyWorkflow = Workflow(spec = "spec2.xml", owner = "Simon",
                                name = "wf003", task='Test')
        dummyWorkflow.create()
         
        acquireSubscription = Subscription(fileset = testFileset,
                                        workflow = dummyWorkflow)
        acquireSubscription.create()        
        acquireSubscription.acquireFiles()

        testSubscription.acquireFiles([testFileA, testFileC])
        acquiredFiles = testSubscription.filesOfStatus(status = "Acquired")

        goldenFiles = [testFileA, testFileC]
        for acquiredFile in acquiredFiles:
            assert acquiredFile in goldenFiles, \
                   "ERROR: Unknown acquired file"
            goldenFiles.remove(acquiredFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Missing acquired files"

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        return

    def testAcquireFilesTransaction(self):
        """
        _testAcquireFilesTransaction_

        Create a subscription and acquire some files from it's input fileset.
        Rollback the transaction and verify that the files are no longer marked
        as acquired.
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
         
        testSubscription.create()

        myThread = threading.currentThread()
        myThread.transaction.begin()

        testSubscription.acquireFiles([testFileA, testFileC])
        acquiredFiles = testSubscription.filesOfStatus(status = "Acquired")

        goldenFiles = [testFileA, testFileC]
        for acquiredFile in acquiredFiles:
            assert acquiredFile in goldenFiles, \
                   "ERROR: Unknown acquired file"
            goldenFiles.remove(acquiredFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Missing acquired files"

        myThread.transaction.rollback()
        acquiredFiles = testSubscription.filesOfStatus(status = "Acquired")
        
        assert len(acquiredFiles) == 0, \
               "ERROR: Transaction didn't roll back acquired files."

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        return    

    def testAvailableFiles(self):
        """
        _testAvailableFiles_

        Create a subscription and mark a couple files as failed, complete and
        acquired.  Test to make sure that the remainder of the files show up
        as available.
        """
        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task='Test')
        testWorkflow.create()

        testFileA = File(lfn = "/this/is/a/lfnA", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileB = File(lfn = "/this/is/a/lfnB", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileC = File(lfn = "/this/is/a/lfnC", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileD = File(lfn = "/this/is/a/lfnD", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileE = File(lfn = "/this/is/a/lfnE", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileF = File(lfn = "/this/is/a/lfnF", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileA.create()
        testFileB.create()
        testFileC.create()
        testFileD.create()
        testFileE.create()
        testFileF.create()        
        
        testFileset = Fileset(name = "TestFileset")
        testFileset.create()
        
        testFileset.addFile(testFileA)
        testFileset.addFile(testFileB)
        testFileset.addFile(testFileC)
        testFileset.addFile(testFileD)
        testFileset.addFile(testFileE)
        testFileset.addFile(testFileF)
        testFileset.commit()

        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription.create()

        testSubscription.acquireFiles([testFileA])
        testSubscription.completeFiles([testFileB])
        testSubscription.failFiles([testFileC])
        availableFiles = testSubscription.availableFiles()

        goldenFiles = [testFileD, testFileE, testFileF]
        for availableFile in availableFiles:
            assert availableFile in goldenFiles, \
                   "ERROR: Unknown available file"
            goldenFiles.remove(availableFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Missing available files"

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        testFileD.delete()
        testFileE.delete()
        testFileF.delete()        
        return

    def testAvailableFilesMeta(self):
        """
        _testAvailableFilesMeta_

        Create a subscription and mark a couple files as failed, complete and
        acquired.  Test to make sure that the remainder of the files show up
        as available using the GetAvailableFilesMeta DAO object.
        """
        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task='Test')
        testWorkflow.create()

        testFileA = File(lfn = "/this/is/a/lfnA", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileB = File(lfn = "/this/is/a/lfnB", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileC = File(lfn = "/this/is/a/lfnC", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileD = File(lfn = "/this/is/a/lfnD", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileD.addRun(Run(1, *[45]))
        testFileD.addRun(Run(2, *[45]))
        testFileE = File(lfn = "/this/is/a/lfnE", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileE.addRun(Run(1, *[45]))
        testFileE.addRun(Run(2, *[45]))        
        testFileF = File(lfn = "/this/is/a/lfnF", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileF.addRun(Run(1, *[45]))
        testFileF.addRun(Run(2, *[45]))        
        testFileA.create()
        testFileB.create()
        testFileC.create()
        testFileD.create()
        testFileE.create()
        testFileF.create()        
        
        testFileset = Fileset(name = "TestFileset")
        testFileset.create()
        
        testFileset.addFile(testFileA)
        testFileset.addFile(testFileB)
        testFileset.addFile(testFileC)
        testFileset.addFile(testFileD)
        testFileset.addFile(testFileE)
        testFileset.addFile(testFileF)
        testFileset.commit()

        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription.create()

        testSubscription.acquireFiles([testFileA])
        testSubscription.completeFiles([testFileB])
        testSubscription.failFiles([testFileC])

        availAction = self.daofactory(classname = "Subscriptions.GetAvailableFilesMeta")
        availableFiles = availAction.execute(subscription = testSubscription["id"])

        testFileDDict = {"id": testFileD["id"], "lfn": testFileD["lfn"],
                         "size": testFileD["size"], "events": testFileD["events"],
                         "run": 1}
        testFileEDict = {"id": testFileE["id"], "lfn": testFileE["lfn"],
                         "size": testFileE["size"], "events": testFileE["events"],
                         "run": 1}
        testFileFDict = {"id": testFileF["id"], "lfn": testFileF["lfn"],
                         "size": testFileF["size"], "events": testFileF["events"],
                         "run": 1}

        goldenFiles = [testFileDDict, testFileEDict, testFileFDict]
        for availableFile in availableFiles:
            assert availableFile in goldenFiles, \
                   "ERROR: Unknown available file: %s" % availableFile
            goldenFiles.remove(availableFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Missing available files"

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        testFileD.delete()
        testFileE.delete()
        testFileF.delete()        
        return    

    def testAvailableFilesTransaction(self):
        """
        _testAvailableFilesTransaction_

        Create a subscription and mark a couple of it's input files as
        complete, failed and acquired.  Rollback the transactions and verify
        that all the files are listed as available.
        """
        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task='Test')
        testWorkflow.create()

        testFileA = File(lfn = "/this/is/a/lfnA", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileB = File(lfn = "/this/is/a/lfnB", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileC = File(lfn = "/this/is/a/lfnC", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileD = File(lfn = "/this/is/a/lfnD", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileE = File(lfn = "/this/is/a/lfnE", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileF = File(lfn = "/this/is/a/lfnF", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileA.create()
        testFileB.create()
        testFileC.create()
        testFileD.create()
        testFileE.create()
        testFileF.create()        
        
        testFileset = Fileset(name = "TestFileset")
        testFileset.create()
        
        testFileset.addFile(testFileA)
        testFileset.addFile(testFileB)
        testFileset.addFile(testFileC)
        testFileset.addFile(testFileD)
        testFileset.addFile(testFileE)
        testFileset.addFile(testFileF)
        testFileset.commit()

        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription.create()

        myThread = threading.currentThread()
        myThread.transaction.begin()

        testSubscription.acquireFiles([testFileA])
        testSubscription.completeFiles([testFileB])
        testSubscription.failFiles([testFileC])
        availableFiles = testSubscription.availableFiles()

        goldenFiles = [testFileD, testFileE, testFileF]
        for availableFile in availableFiles:
            assert availableFile in goldenFiles, \
                   "ERROR: Unknown available file"
            goldenFiles.remove(availableFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Missing available files"

        myThread.transaction.rollback()
        availableFiles = testSubscription.availableFiles()        

        goldenFiles = [testFileA, testFileB, testFileC, testFileD, testFileE,
                       testFileF]

        for availableFile in availableFiles:
            assert availableFile in goldenFiles, \
                   "ERROR: Unknown available file"
            goldenFiles.remove(availableFile)



        assert len(goldenFiles) == 0, \
               "ERROR: Missing available files after rollback."

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        testFileD.delete()
        testFileE.delete()
        testFileF.delete()        
        return    
    
    def testAvailableFilesWhiteList(self):
        """
        _testAvailableFilesWhiteList_
        
        Testcase for the availableFiles method of the Subscription Class when a 
        white list is present in the subscription.
        """
        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task='Test')
        testWorkflow.create()

        testFileset = Fileset(name = "TestFileset")
        testFileset.create()
        
        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription.create()
        
        count = 0
        for i in range(0, 100):
            lfn = "/store/data/%s/%s/file.root" % (random.randint(1000, 9999),
                                                   random.randint(1000, 9999))
            size = random.randint(1000, 2000)
            events = 1000
            run = random.randint(0, 2000)
            lumi = random.randint(0, 8)
    
            testFile = File(lfn=lfn, size=size, events=events)
            testFile.addRun(Run(run, *[lumi]))
            testFile.create()
            
            if random.randint(1, 2) > 1:
                testFile.setLocation("goodse.cern.ch")
                count += 1
            else:
                testFile.setLocation("badse.cern.ch")

            testFileset.addFile(testFile)
            
        testFileset.commit()
        testSubscription.markLocation("site1")
        
        assert count == len(testSubscription.availableFiles()), \
        "Subscription has %s files available, should have %s" % \
        (len(testSubscription.availableFiles()), count)
        
    def testAvailableFilesBlackList(self):
        """
        _testAvailableFilesBlackList_
        
        Testcase for the availableFiles method of the Subscription Class
        """
        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task='Test')
        testWorkflow.create()

        testFileset = Fileset(name = "TestFileset")
        testFileset.create()
        
        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription.create()
        
        count = 0
        for i in range(0, 100):
            lfn = "/blacklist/%s/%s/file.root" % (random.randint(1000, 9999),
                                                  random.randint(1000, 9999))
            size = random.randint(1000, 2000)
            events = 1000
            run = random.randint(0, 2000)
            lumi = random.randint(0, 8)
    
            testFile = File(lfn=lfn, size=size, events=events)
            testFile.addRun(Run(run, *[lumi]))
            testFile.create()
            
            if random.randint(1, 2) > 1:
                testFile.setLocation("goodse.cern.ch")
            else:
                testFile.setLocation("badse.cern.ch")
                count += 1
                
            testFileset.addFile(testFile)
        testFileset.commit()
        
        testSubscription.markLocation("site3", whitelist = False)
        assert 100 - count == len(testSubscription.availableFiles()), \
        "Subscription has %s files available, should have %s" %\
        (len(testSubscription.availableFiles()), 100 - count) 
               
    def testAvailableFilesBlackWhiteList(self):
        """
        _testAvailableFilesBlackWhiteList_
        
        Testcase for the availableFiles method of the Subscription Class when 
        both a white and black list are provided
        """
        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task='Test')
        testWorkflow.create()

        testFileset = Fileset(name = "TestFileset")
        testFileset.create()
        
        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription.create()
        
        count = 0
        for i in range(0, 10):
            lfn = "/store/data/%s/%s/file.root" % (random.randint(1000, 9999),
                                                   random.randint(1000, 9999))
            size = random.randint(1000, 2000)
            events = 1000
            run = random.randint(0, 2000)
            lumi = random.randint(0, 8)
    
            testFile = File(lfn=lfn, size=size, events=events)
            testFile.addRun(Run(run, *[lumi]))
            testFile.create()
            
            if random.randint(1, 2) > 1:
                testFile.setLocation("goodse.cern.ch")
                count += 1
            else:
                testFile.setLocation("badse.cern.ch")

            testFileset.addFile(testFile)
           
        testFileset.commit()   
        testSubscription.markLocation("site3", whitelist = False)
        testSubscription.markLocation("site1")
        
        assert count == len(testSubscription.availableFiles()), \
        "Subscription has %s files available, should have %s" %\
        (len(testSubscription.availableFiles()), count)   

    def testLoad(self):
        """
        _testLoad_

        Create a subscription and save it to the database.  Test the various
        load methods to make sure that everything saves/loads.
        """
        (testSubscriptionA, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
         
        testSubscriptionA.create()

        testSubscriptionB = Subscription(id = testSubscriptionA["id"])
        testSubscriptionC = Subscription(workflow = testSubscriptionA["workflow"],
                                         fileset = testSubscriptionA["fileset"],
                                         type = testSubscriptionA["type"])
        testSubscriptionB.load()
        testSubscriptionC.load()

        assert type(testSubscriptionB["id"]) == int, \
               "ERROR: Subscription id is not an int."

        assert type(testSubscriptionC["id"]) == int, \
               "ERROR: Subscription id is not an int."        

        assert type(testSubscriptionB["workflow"].id) == int, \
               "ERROR: Subscription workflow id is not an int."

        assert type(testSubscriptionC["workflow"].id) == int, \
               "ERROR: Subscription workflow id is not an int."        

        assert type(testSubscriptionB["fileset"].id) == int, \
               "ERROR: Subscription fileset id is not an int."

        assert type(testSubscriptionC["fileset"].id) == int, \
               "ERROR: Subscription fileset id is not an int."        

        assert testWorkflow.id == testSubscriptionB["workflow"].id, \
               "ERROR: Subscription load by ID didn't load workflow correctly"

        assert testFileset.id == testSubscriptionB["fileset"].id, \
               "ERROR: Subscription load by ID didn't load fileset correctly"        

        assert testSubscriptionA["id"] == testSubscriptionC["id"], \
               "ERROR: Subscription didn't load ID correctly."

        return

    def testLoadData(self):
        """
        _testLoadData_

        Test the Subscription's loadData() method to make sure that everything
        that should be loaded is loaded correctly.
        """
        (testSubscriptionA, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
         
        testSubscriptionA.create()

        testSubscriptionB = Subscription(id = testSubscriptionA["id"])
        testSubscriptionC = Subscription(workflow = testSubscriptionA["workflow"],
                                         fileset = testSubscriptionA["fileset"])
        testSubscriptionB.loadData()
        testSubscriptionC.loadData()

        assert (testWorkflow.id == testSubscriptionB["workflow"].id) and \
               (testWorkflow.name == testSubscriptionB["workflow"].name) and \
               (testWorkflow.spec == testSubscriptionB["workflow"].spec) and \
               (testWorkflow.owner == testSubscriptionB["workflow"].owner), \
               "ERROR: Workflow.LoadFromID Failed"

        assert testFileset.id == testSubscriptionB["fileset"].id, \
               "ERROR: Load didn't load fileset id"

        assert testFileset.name == testSubscriptionB["fileset"].name, \
               "ERROR: Load didn't load fileset name"

        goldenFiles = [testFileA, testFileB, testFileC]
        for filesetFile in testSubscriptionB["fileset"].files:
            assert filesetFile in goldenFiles, \
                   "ERROR: Unknown file in fileset"
            goldenFiles.remove(filesetFile)

        assert len(goldenFiles) == 0, \
               "ERROR: Fileset is missing files"

        assert testSubscriptionA["id"] == testSubscriptionC["id"], \
               "ERROR: Subscription didn't load ID correctly."

        return

    def testSubscriptionList(self):
        """
        _testSubscriptionList_

        Create two subscriptions and verify that the Subscriptions.List DAO
        object returns their IDs.
        """
        testWorkflowA = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task='Test')
        testWorkflowB = Workflow(spec = "spec2.xml", owner = "Simon",
                                name = "wf002", task='Test')
        testWorkflowA.create()
        testWorkflowB.create()        

        testFileset = Fileset(name = "TestFileset")
        testFileset.create()

        testSubscriptionA = Subscription(fileset = testFileset,
                                         workflow = testWorkflowA)
        testSubscriptionB = Subscription(fileset = testFileset,
                                         workflow = testWorkflowB)        
        testSubscriptionA.create()
        testSubscriptionB.create()        
        
        myThread = threading.currentThread()
        daofactory = DAOFactory(package = "WMCore.WMBS",
                                logger = myThread.logger,
                                dbinterface = myThread.dbi)
        
        subListAction = daofactory(classname = "Subscriptions.List")        
        subIDs = subListAction.execute()

        assert len(subIDs) == 2, \
               "ERROR: Too many subscriptions returned."

        assert testSubscriptionA["id"] in subIDs, \
               "ERROR: Subscription A is missing."

        assert testSubscriptionB["id"] in subIDs, \
               "ERROR: Subscription B is missing."

        return
    
    def testSubscriptionCompleteStatusByRun(self):
        """
        _testSubscriptionCompleteStatusByRun_
        
        test status for a given subscription and given run 
        testFileA, testFileB is in run 1
        testFileC is in run 2
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
        testSubscription.create()
        
        files = testSubscription.filesOfStatusByRun("Available", 1)
        self.assertEqual( len(files) ,  2, "2 files should be available for run 1" )
        
        files = testSubscription.filesOfStatusByRun("Available", 2)
        self.assertEqual( len(files) ,  1, "1 file should be available for run 2" )
        self.assertEqual( files[0] ,  testFileC,  "That file shoulb be testFileC" )
        
        files = testSubscription.filesOfStatusByRun("Completed", 1)
        self.assertEqual( len(files) ,  0, "No files shouldn't be completed for run 1" )
        
        files = testSubscription.filesOfStatusByRun("Completed", 2)
        self.assertEqual( len(files) ,  0, "No files shouldn't be completed for run 2" )
        
        files = testSubscription.filesOfStatusByRun("Failed", 1)
        self.assertEqual( len(files) ,  0, "No files shouldn't be failed for run 1" )
        
        files = testSubscription.filesOfStatusByRun("Failed", 2)
        self.assertEqual( len(files) ,  0, "No files shouldn't be failed for run 2" )
            
        assert testSubscription.isCompleteOnRun(1) == False, \
               "Run 1 shouldn't be completed."
        
        assert testSubscription.isCompleteOnRun(2) == False, \
               "Run 2 shouldn't be completed."
                
        testSubscription.completeFiles([testFileA, testFileB])
        
        files = testSubscription.filesOfStatusByRun("Available", 1)
        self.assertEqual( len(files) ,  0, "0 files should be available for run 1" )
        
        files = testSubscription.filesOfStatusByRun("Available", 2)
        self.assertEqual( len(files) ,  1, "1 file should be available for run 2" )
        
        files = testSubscription.filesOfStatusByRun("Completed", 1)
        self.assertEqual( len(files) ,  2, "2 files should completed for run 1" )
        
        files = testSubscription.filesOfStatusByRun("Completed", 2)
        self.assertEqual( len(files) ,  0, "No files shouldn't be completed for run 2" )
        
        files = testSubscription.filesOfStatusByRun("Failed", 1)
        self.assertEqual( len(files) ,  0, "No files shouldn't be failed for run 1" )
        
        files = testSubscription.filesOfStatusByRun("Failed", 2)
        self.assertEqual( len(files) ,  0, "No files shouldn't be failed for run 2" )
        
        assert testSubscription.isCompleteOnRun(1) == True, \
               "Run 1 should be completed."
        
        assert testSubscription.isCompleteOnRun(2) == False, \
               "Run 2 shouldn't be completed."
        
        testSubscription.failFiles([testFileA, testFileC])
        
        files = testSubscription.filesOfStatusByRun("Available", 1)
        self.assertEqual( len(files) ,  0, "0 files should be available for run 1" )
        
        files = testSubscription.filesOfStatusByRun("Available", 2)
        self.assertEqual( len(files) ,  0, "0 file should be available for run 2" )
        
        files = testSubscription.filesOfStatusByRun("Completed", 1)
        self.assertEqual( len(files) ,  1, "1 file should be completed for run 1" )
        self.assertEqual( files[0] ,  testFileB,  "That file shoulb be testFileB" )
        
        files = testSubscription.filesOfStatusByRun("Completed", 2)
        self.assertEqual( len(files) ,  0, "No files shouldn't be completed for run 2" )
        
        files = testSubscription.filesOfStatusByRun("Failed", 1)
        self.assertEqual( len(files) ,  1, "1 file should be failed for run 1" )
        
        files = testSubscription.filesOfStatusByRun("Failed", 2)
        self.assertEqual( len(files) ,  1, "1 files should be failed for run 2" )
        
        
        assert testSubscription.isCompleteOnRun(1) == True, \
               "Run 1 should be completed."
        assert testSubscription.isCompleteOnRun(2) == True, \
               "Run 2 should be completed."



    def testGetNumberOfJobsPerSite(self):
        """
        Test for a JobCreator specific function
        
        """
        
        myThread = threading.currentThread()

        testSubscription, testFileset, testWorkflow, testFileA, testFileB, testFileC = self.createSubscriptionWithFileABC()

        testSubscription.create()
        
        testJobGroup = JobGroup(subscription = testSubscription)
        testJobGroup.create()
        
        jobA = Job(name = 'testA')
        jobA.addFile(testFileA)
        jobA["location"] = "site1"
        jobA.create(testJobGroup)
        
        jobB = Job(name = 'testB')
        jobB.addFile(testFileB)
        jobB["location"] = "site1"
        jobB.create(testJobGroup)
        
        jobC = Job(name = 'testC')
        jobC.addFile(testFileC)
        jobC["location"] = "site1"
        jobC.create(testJobGroup)
        
        testJobGroup.add(jobA)
        testJobGroup.add(jobB)
        testJobGroup.add(jobC)
        
        testJobGroup.commit()

        nJobs = testSubscription.getNumberOfJobsPerSite('site1', 'new')
        
        self.assertEqual(nJobs, 3)
        
        nZero = testSubscription.getNumberOfJobsPerSite('site3', 'new')
        
        self.assertEqual(nZero, 0)
        
        return
            
    def testListIncompleteDAO(self):
        """
        _testListIncompeteDAO_

        Test the Subscription.ListIncomplete DAO object that returns a list of
        the subscriptions that have not completed processing all files.
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
        testSubscription.create()

        myThread = threading.currentThread()        
        daoFactory = DAOFactory(package="WMCore.WMBS", logger = myThread.logger,
                                dbinterface = myThread.dbi)

        subIncomplete = daoFactory(classname = "Subscriptions.ListIncomplete")

        incompleteSubs = subIncomplete.execute()

        assert len(incompleteSubs) == 2, \
               "ERROR: Wrong number of incomplete subscriptions returned: %s" % len(incompleteSubs)
        assert testSubscription["id"] in incompleteSubs, \
               "ERROR: Original subscription is missing."

        otherSub = None
        for subId in incompleteSubs:
            if subId != testSubscription["id"]:
                otherSub = subId

        incompleteSub = subIncomplete.execute(minSub = min(incompleteSubs) + 1)

        assert len(incompleteSub) == 1, \
               "ERROR: Only one subscription should be returned: %s" % incompleteSub

        testSubscription.completeFiles([testFileA, testFileB, testFileC])

        incompleteSubs = subIncomplete.execute()

        assert len(incompleteSubs) == 1, \
               "ERROR: Wrong number of incomplete subscriptions returned."
        assert otherSub in incompleteSubs, \
               "ERROR: Wrong subscription ID returned."

        return
    
    def testGetJobGroups(self):
        """
        _testGetJobGroups_
        
        Verify that the getJobGroups() method will return a list of JobGroups
        that contain jobs that have not been acquired/completed/failed.
        """
        (testSubscription, testFileset, testWorkflow, testFileA, \
            testFileB, testFileC) = self.createSubscriptionWithFileABC()
        testSubscription.create()

        stateChanger = ChangeState(DefaultConfig.config)

        testJobGroupA = JobGroup(subscription = testSubscription)
        testJobGroupA.create()

        testJobA = Job(name = "TestJobA")
        testJobA.addFile(testFileA)
        
        testJobB = Job(name = "TestJobB")
        testJobB.addFile(testFileB)
        
        testJobGroupA.add(testJobA)
        testJobGroupA.add(testJobB)
        testJobGroupA.commit()
       
        testJobGroupB = JobGroup(subscription = testSubscription)
        testJobGroupB.create()

        testFileD = File(lfn = "/this/is/a/lfnD", size = 1024, events = 10)
        testFileD.addRun(Run(10, *[12312]))
        testFileD.create()

        testJobC = Job(name = "TestJobC")
        testJobC.addFile(testFileC)
        
        testJobD = Job(name = "TestJobD")
        testJobD.addFile(testFileD)
        
        testJobGroupB.add(testJobC)
        testJobGroupB.add(testJobD)
        testJobGroupB.commit() 

        firstResult = testSubscription.getJobGroups()
        for jobGroup in [testJobGroupA.id, testJobGroupB.id]:
            assert jobGroup in firstResult, \
                   "Error: jobgroup %s is missing. " % jobGroup
            firstResult.remove(jobGroup)

        assert len(firstResult) == 0, \
               "Error: Too monay job groups in result."
        
        stateChanger.propagate([testJobA], "created", "new")
        secondResult = testSubscription.getJobGroups()
        for jobGroup in [testJobGroupA.id, testJobGroupB.id]:
            assert jobGroup in secondResult, \
                   "Error: jobgroup %s is missing. " % jobGroup
            secondResult.remove(jobGroup)

        assert len(secondResult) == 0, \
               "Error: Too monay job groups in result."
        
        stateChanger.propagate([testJobB], "created", "new")
        thirdResult = testSubscription.getJobGroups()
        for jobGroup in [testJobGroupB.id]:
            assert jobGroup in thirdResult, \
                   "Error: jobgroup %s is missing. " % jobGroup
            thirdResult.remove(jobGroup)

        assert len(thirdResult) == 0, \
               "Error: Too monay job groups in result."
        
        return

    def testDeleteEverything(self):
        """
        _testDeleteEverything_
        
        Tests the delete function that should delete all component of a subscription
        """

        myThread = threading.currentThread()

        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task = "Test")
        testWorkflow.create()

        testFileA = File(lfn = "/this/is/a/lfnA", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileA.addRun(Run(1, *[45]))
                                 
        testFileB = File(lfn = "/this/is/a/lfnB", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))                         
        testFileB.addRun(Run(1, *[45]))
        
        testFileC = File(lfn = "/this/is/a/lfnC", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileC.addRun(Run(2, *[48]))

        testFileD = File(lfn = "/this/is/a/lfnD", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileD.addRun(Run(2, *[48]))

        testFile1 = File(lfn = "/this/is/a/lfn1", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]), merged = False)
        testFile1.addRun(Run(2, *[48]))

        testFile2 = File(lfn = "/this/is/a/lfn2", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]), merged = False)
        testFile2.addRun(Run(2, *[48]))

        testFileA.create()
        testFileB.create()
        testFileC.create()
        testFileD.create()
        testFile1.create()
        testFileA.addChild(testFile1['lfn'])

        
        logging.info("About to test fileset deletes")

        testFileset = Fileset(name = "TestFileset")
        testFileset.create()

        testFileset2 = Fileset(name = "TestFileset2")
        testFileset2.create()
        
        testFileset.addFile(testFileA)
        testFileset.addFile(testFileB)
        testFileset.addFile(testFileC)
        testFileset.addFile(testFileD)
        testFileset.commit()

        testFilesetQ = Fileset(name = "TestFilesetQ")
        testFilesetQ.create()
        # Put it in the workflow
        testWorkflow.addOutput(outputIdentifier = 'a', outputFileset = testFilesetQ)

        testFileset2.addFile(testFileD)
        testFileset2.commit()

        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription.create()
        testSubscription2 = Subscription(fileset = testFileset2,
                                         workflow = testWorkflow)
        testSubscription2.create()

        testJobGroupA = JobGroup(subscription = testSubscription)
        testJobGroupA.create()

        testJobA = Job(name = "TestJobA")
        testJobA.addFile(testFileA)
        
        testJobB = Job(name = "TestJobB")
        testJobB.addFile(testFileB)

        testJobGroupA.add(testJobA)
        testJobGroupA.add(testJobB)
        testJobGroupA.output.addFile(testFile1)
        testJobGroupA.output.addFile(testFile2)
        testJobGroupA.output.commit()

        testJobGroupA.commit()
        testSubscription.save()

        testSubscription.deleteEverything()

        self.assertEqual(testSubscription.exists(), False)
        self.assertEqual(testWorkflow.exists(), 1)
        self.assertEqual(testFileset.exists(),  False)
        self.assertEqual(testFileset2.exists(), 2)

        result = myThread.dbi.processData("SELECT * FROM wmbs_job")[0].fetchall()
        self.assertEqual(len(result), 0)
        result = myThread.dbi.processData("SELECT * FROM wmbs_jobgroup")[0].fetchall()
        self.assertEqual(len(result), 0)
        self.assertFalse(testJobGroupA.output.exists())
        self.assertEqual(testFile1.exists(), False)
        self.assertEqual(testFile2.exists(), False)
        self.assertFalse(testFilesetQ.exists())
        self.assertEqual(testFileA.exists(), False)
        self.assertEqual(testFileB.exists(), False)
        self.assertEqual(testFileC.exists(), False)
        self.assertEqual(testFileD.exists(), 4)
        
    def testIsFileCompleted(self):
        """
        _testIsFileCompleted_

        Test file completion markings
        """
        (testSubscription, testFileset, testWorkflow, 
         testFileA, testFileB, testFileC) = self.createSubscriptionWithFileABC()
         
        testSubscription.create()

        myThread = threading.currentThread()
        myThread.transaction.begin()
        
        testSubscription.completeFiles([testFileA, testFileC])
        
        assert testSubscription.isFileCompleted(testFileA) == True, \
            "ERROR: file A should be completed"
        assert testSubscription.isFileCompleted([testFileA, testFileC]) == True, \
            "ERROR: file A, C should be completed"
        assert testSubscription.isFileCompleted([testFileA, 
                                                 testFileB, 
                                                 testFileC]) == False, \
            "ERROR: file A, B, C shouldn't be completed"
        
        assert testSubscription.isFileCompleted(testFileB) == False, \
            "ERROR: file B shouldn't be completed"

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()        
        return


    def testGetSubTypes(self):
        """
        _testGetSubTypes_
        
        Test the getSubTypes function
        """
        myThread   = threading.currentThread()
        daoFactory = DAOFactory(package="WMCore.WMBS", logger = myThread.logger,
                                dbinterface = myThread.dbi)
        
        getSubTypes = daoFactory(classname = "Subscriptions.GetSubTypes")

        result = getSubTypes.execute()

        self.assertEqual(len(result), 6, "Error: Wrong number of types.")
        for subType in ["Processing", "Merge", "Harvesting", "Cleanup", "LogCollect", "Skim"]:
            self.assertTrue(subType in result, "Type %s is missing" % (subType))

        return


    def testBulkCommit(self):
        """
        _testBulkCommit_

        Test committing everything in bulk
        """

        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task = "Test")
        testWorkflow.create()

        testFileA = File(lfn = "/this/is/a/lfnA", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileA.addRun(Run(1, *[45]))
                                 
        testFileB = File(lfn = "/this/is/a/lfnB", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))                         
        testFileB.addRun(Run(1, *[45]))
        
        testFileC = File(lfn = "/this/is/a/lfnC", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileC.addRun(Run(2, *[48]))

        testFileD = File(lfn = "/this/is/a/lfnD", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileD.addRun(Run(2, *[48]))
         
        testFileA.create()
        testFileB.create()
        testFileC.create()
        testFileD.create()


        
        testFileset = Fileset(name = "TestFileset")
        testFileset.create()

        testFileset2 = Fileset(name = "TestFileset2")
        testFileset2.create()
        
        testFileset.addFile(testFileA)
        testFileset.addFile(testFileB)
        testFileset.addFile(testFileC)
        testFileset.addFile(testFileD)
        testFileset.commit()


        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription.create()

        # Everything above here has to exist before we get started

        testJobGroupA = JobGroup(subscription = testSubscription)
        testJobGroupB = JobGroup(subscription = testSubscription)

        testJobA = Job(name = "TestJobA")
        testJobA.addFile(testFileA)
        
        testJobB = Job(name = "TestJobB")
        testJobB.addFile(testFileB)

        testJobC = Job(name = "TestJobC")
        testJobC.addFile(testFileC)
        
        testJobD = Job(name = "TestJobD")
        testJobD.addFile(testFileD)

        testJobGroupA.add(testJobA)
        testJobGroupA.add(testJobB)
        testJobGroupB.add(testJobC)
        testJobGroupB.add(testJobD)

        testSubscription.bulkCommit(jobGroups = [testJobGroupA, testJobGroupB])

        self.assertEqual(testJobA.exists() > 0, True)
        self.assertEqual(testJobB.exists() > 0, True)
        self.assertEqual(testJobC.exists() > 0, True)
        self.assertEqual(testJobD.exists() > 0, True)
        self.assertEqual(testJobGroupA.exists() > 0, True)
        self.assertEqual(testJobGroupB.exists() > 0, True)


        result = testSubscription.filesOfStatus(status = "Acquired")
        self.assertEqual(len(result), 4,
                         'Should have acquired 4 files, instead have %i' %(len(result)))
        self.assertEqual(len(testJobGroupA.jobs), 2)


        return
        

    def testFilesOfStatusByLimit(self):
        """
        _testFilesOfstatusByLimit_

        Create a subscription and mark a couple files as failed, complete and
        acquired.  Test to make sure that the remainder of the files show up
        as available.
        """
        testWorkflow = Workflow(spec = "spec.xml", owner = "Simon",
                                name = "wf001", task='Test')
        testWorkflow.create()

        testFileA = File(lfn = "/this/is/a/lfnA", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileB = File(lfn = "/this/is/a/lfnB", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileC = File(lfn = "/this/is/a/lfnC", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileD = File(lfn = "/this/is/a/lfnD", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileE = File(lfn = "/this/is/a/lfnE", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileF = File(lfn = "/this/is/a/lfnF", size = 1024, events = 20,
                         locations = set(["goodse.cern.ch"]))
        testFileA.create()
        testFileB.create()
        testFileC.create()
        testFileD.create()
        testFileE.create()
        testFileF.create()        
        
        testFileset = Fileset(name = "TestFileset")
        testFileset.create()
        
        testFileset.addFile(testFileA)
        testFileset.addFile(testFileB)
        testFileset.addFile(testFileC)
        testFileset.addFile(testFileD)
        testFileset.addFile(testFileE)
        testFileset.addFile(testFileF)
        testFileset.commit()

        testSubscription = Subscription(fileset = testFileset,
                                        workflow = testWorkflow)
        testSubscription.create()
        
        availableFiles = testSubscription.filesOfStatus("Available")
        self.assertEquals(len(availableFiles), 6)
        availableFiles = testSubscription.filesOfStatus("Available", 0)
        self.assertEquals(len(availableFiles), 6)
        availableFiles = testSubscription.filesOfStatus("Available", 3)
        self.assertEquals(len(availableFiles), 3)
        availableFiles = testSubscription.filesOfStatus("Available", 7)
        self.assertEquals(len(availableFiles), 6)
        
        
        testSubscription.acquireFiles([testFileA, testFileB, testFileC, testFileD])
        availableFiles = testSubscription.filesOfStatus("Available", 6)
        self.assertEquals(len(availableFiles), 2)
        
        files = testSubscription.filesOfStatus("Acquired", 0)
        self.assertEquals(len(files), 4)
        files = testSubscription.filesOfStatus("Acquired", 2)
        self.assertEquals(len(files), 2)
        files = testSubscription.filesOfStatus("Acquired", 6)
        self.assertEquals(len(files), 4)
        
        
        testSubscription.completeFiles([testFileB, testFileC])
        
        files = testSubscription.filesOfStatus("Completed", 0)
        self.assertEquals(len(files), 2)
        files = testSubscription.filesOfStatus("Completed", 1)
        self.assertEquals(len(files), 1)
        files = testSubscription.filesOfStatus("Completed", 6)
        self.assertEquals(len(files), 2)
        
        testSubscription.failFiles([testFileA, testFileE])
        
        files = testSubscription.filesOfStatus("Failed", 0)
        self.assertEquals(len(files), 2)
        files = testSubscription.filesOfStatus("Failed", 1)
        self.assertEquals(len(files), 1)
        files = testSubscription.filesOfStatus("Failed", 6)
        self.assertEquals(len(files), 2)
        

        testSubscription.delete()
        testWorkflow.delete()
        testFileset.delete()
        testFileA.delete()
        testFileB.delete()
        testFileC.delete()
        testFileD.delete()
        testFileE.delete()
        testFileF.delete()        
        return


if __name__ == "__main__":
    unittest.main()
