import wx
from logbook import Logger

import eos.db
from gui.fitCommands.helpers import ModuleInfo
from service.fit import Fit


pyfalog = Logger(__name__)


class CalcRemoveLocalModuleCommand(wx.Command):

    def __init__(self, fitID, positions, commit=True):
        wx.Command.__init__(self, True, 'Remove Module')
        self.fitID = fitID
        self.positions = positions
        self.savedModInfos = {}
        self.commit = commit

    def Do(self):
        pyfalog.debug('Doing removal of local modules from positions {} on fit {}'.format(self.positions, self.fitID))
        fit = Fit.getInstance().getFit(self.fitID)

        for position in self.positions:
            mod = fit.modules[position]
            if not mod.isEmpty:
                self.savedModInfos[position] = ModuleInfo.fromModule(mod)
                fit.modules.free(position)

        if self.commit:
            eos.db.commit()
        # If no modules were removed, report that command was not completed
        return len(self.savedModInfos) > 0

    def Undo(self):
        pyfalog.debug('Undoing removal of local modules {} on fit {}'.format(self.savedModInfos, self.fitID))
        results = []
        from .localReplace import CalcReplaceLocalModuleCommand
        for position, modInfo in self.savedModInfos.items():
            cmd = CalcReplaceLocalModuleCommand(fitID=self.fitID, position=position, newModInfo=modInfo, commit=False)
            results.append(cmd.Do())
        if self.commit:
            eos.db.commit()
        return any(results)