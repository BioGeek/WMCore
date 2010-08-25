import os
import unittest
import mox
import WMCore_t.Storage_t.Plugins_t.PluginTestBase_t
from WMCore.Storage.Plugins.DCCPFNALImpl import DCCPFNALImpl as ourPlugin

from WMCore.Storage.Plugins.CPImpl import CPImpl as ourFallbackPlugin
import WMCore.Storage.Plugins.DCCPFNALImpl
import subprocess
from WMCore.WMBase import getWMBASE
from WMCore.Storage.StageOutError import StageOutError, StageOutFailure

class RunCommandThing:
    def __init__(self, target):
        self.target = target
    def runCommand(self,things):
        return ("dummy1", "dummy2")
    

class DCCPFNALImplTest(unittest.TestCase):
    
    def setUp(self):
        self.commandPrepend = os.path.join(getWMBASE(),'src','python','WMCore','Storage','Plugins','DDCPFNAL','wrapenv.sh')
        pass
    
    def tearDown(self):
        pass
    
    def testFail(self):

        runMocker  = mox.MockObject(RunCommandThing)
        copyMocker = mox.MockObject(ourFallbackPlugin)
        def runCommandStub(command):
            (num1, num2) =  runMocker.runCommand(command)
            return (num1, num2)
        def getImplStub(command, useNewVersion = None):
            return copyMocker
        
        WMCore.Storage.Plugins.DCCPFNALImpl.runCommand = runCommandStub
        WMCore.Storage.Plugins.DCCPFNALImpl.retrieveStageOutImpl = getImplStub
        
        #first try to make a non existant file (regular)
        runMocker.runCommand( 
            [self.commandPrepend,'dccp', '-o', '86400', '-d', '0', '-X', '-role=cmsprod', '/store/NONEXISTANTSOURCE', '/store/NONEXISTANTTARGET' ]\
             ).AndReturn(("1", "This was a test of the fail system"))
             
        #then try to make a non existant file on lustre
        # -- fake making a directory
        runMocker.runCommand( 
            [self.commandPrepend, 'mkdir', '-m', '755', '-p', '/store/unmerged']\
             ).AndReturn(("0", "we made a directory, yay"))        
        # -- fake the actual copy
        copyMocker.doTransfer( \
            '/store/unmerged/lustre/NONEXISTANTSOURCE', '/store/unmerged/lustre/NONEXISTANTTARGET', True, None, None, None, None\
             ).AndRaise(StageOutFailure("testFailure"))
        
   
        # now try to delete it (pnfs)
        runMocker.runCommand( 
            ['rm', '-fv', '/pnfs/cms/WAX/11/store/tmp/testfile' ]\
             ).AndReturn(("1", "This was a test of the fail system"))
        # try to delete it (lustre)
        runMocker.runCommand( 
            ['/bin/rm', '/lustre/unmerged/NOTAFILE']\
             ).AndReturn(("1", "This was a test of the fail system"))

        mox.Replay(runMocker)       
        mox.Replay(copyMocker)
        #ourPlugin.runCommand = runMocker.runCommand()
        testObject = ourPlugin()
        
        self.assertRaises(StageOutFailure,
                           testObject.doTransfer,'/store/NONEXISTANTSOURCE',
                              '/store/NONEXISTANTTARGET',
                              True, 
                              None,
                              None,
                              None,
                              None)
        self.assertRaises(StageOutFailure,
                           testObject.doTransfer,'/store/unmerged/lustre/NONEXISTANTSOURCE',
                              '/store/unmerged/lustre/NONEXISTANTTARGET',
                              True, 
                              None,
                              None,
                              None,
                              None)
        testObject.doDelete('/store/tmp/testfile', None, None, None, None  )
        testObject.doDelete('/store/unmerged/lustre/NOTAFILE',None, None, None, None )
        mox.Verify(runMocker)
        mox.Verify(copyMocker)
        

if __name__ == "__main__":
    unittest.main()

