# =============================================================================
# Copyright (C) 2010 Diego Duclos
#
# This file is part of pyfa.
#
# pyfa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyfa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyfa.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================


import math

from eos.const import FittingModuleState
from .base import Graph, XDef, YDef, Input


AU_METERS = 149597870700


class FitWarpTimeGraph(Graph):

    name = 'Warp Time'

    def __init__(self):
        super().__init__()

    # UI stuff
    @property
    def xDefs(self):
        return [
            XDef(handle='distance', unit='AU', label='Distance', mainInput=('distance', 'AU')),
            XDef(handle='distance', unit='km', label='Distance', mainInput=('distance', 'km'))]

    @property
    def yDefs(self):
        return [YDef(handle='time', unit='s', label='Warp time')]

    @property
    def inputs(self):
        return [
            Input(handle='distance', unit='AU', label='Distance', iconID=1391, defaultValue=50, defaultRange=(0, 50), mainOnly=False),
            Input(handle='distance', unit='km', label='Distance', iconID=1391, defaultValue=10000, defaultRange=(150, 5000), mainOnly=False)]

    # Calculation stuff
    _normalizers = {
        ('distance', 'AU'): lambda v, fit, tgt: v * AU_METERS,
        ('distance', 'km'): lambda v, fit, tgt: v * 1000}

    _limiters = {
        'distance': lambda fit, tgt: (0, fit.maxWarpDistance * AU_METERS)}

    _denormalizers = {
        ('distance', 'AU'): lambda v, fit, tgt: v / AU_METERS,
        ('distance', 'km'): lambda v, fit, tgt: v / 1000}

    def _distance2time(self, mainInput, miscInputs, fit, tgt):
        xs = []
        ys = []
        subwarpSpeed = self.__getSubwarpSpeed(fit)
        warpSpeed = fit.warpSpeed
        for distance in self._iterLinear(mainInput[1]):
            time = calculate_time_in_warp(subwarpSpeed, warpSpeed, distance)
            xs.append(distance)
            ys.append(time)
        return xs, ys

    _getters = {
        ('distance', 'time'): _distance2time}

    def __getSubwarpSpeed(self, fit):
        try:
            subwarpSpeed = self._calcCache[fit.ID]['cleanSubwarpSpeed']
        except KeyError:
            modStates = {}
            for mod in fit.modules:
                if mod.item is not None and mod.item.group.name in ('Propulsion Module', 'Mass Entanglers', 'Cloaking Device') and mod.state >= FittingModuleState.ACTIVE:
                    modStates[mod] = mod.state
                    mod.state = FittingModuleState.ONLINE
            projFitStates = {}
            for projFit in fit.projectedFits:
                projectionInfo = projFit.getProjectionInfo(fit.ID)
                if projectionInfo is not None and projectionInfo.active:
                    projFitStates[projectionInfo] = projectionInfo.active
                    projectionInfo.active = False
            projModStates = {}
            for mod in fit.projectedModules:
                if not mod.isExclusiveSystemEffect and mod.state >= FittingModuleState.ACTIVE:
                    projModStates[mod] = mod.state
                    mod.state = FittingModuleState.ONLINE
            projDroneStates = {}
            for drone in fit.projectedDrones:
                if drone.amountActive > 0:
                    projDroneStates[drone] = drone.amountActive
                    drone.amountActive = 0
            projFighterStates = {}
            for fighter in fit.projectedFighters:
                if fighter.active:
                    projFighterStates[fighter] = fighter.active
                    fighter.active = False
            fit.calculateModifiedAttributes()
            subwarpSpeed = fit.ship.getModifiedItemAttr('maxVelocity')
            self._calcCache[fit.ID] = {'cleanSubwarpSpeed': subwarpSpeed}
            for projInfo, state in projFitStates.items():
                projInfo.active = state
            for mod, state in modStates.items():
                mod.state = state
            for mod, state in projModStates.items():
                mod.state = state
            for drone, amountActive in projDroneStates.items():
                drone.amountActive = amountActive
            for fighter, state in projFighterStates.items():
                fighter.active = state
            fit.calculateModifiedAttributes()
        return subwarpSpeed


# Taken from https://wiki.eveuniversity.org/Warp_time_calculation#Implementation
# with minor modifications
# Warp speed in AU/s, subwarp speed in m/s, distance in m
def calculate_time_in_warp(max_warp_speed, max_subwarp_speed, warp_dist):

    if warp_dist == 0:
        return 0

    k_accel = max_warp_speed
    k_decel = min(max_warp_speed / 3, 2)

    warp_dropout_speed = max_subwarp_speed / 2
    max_ms_warp_speed = max_warp_speed * AU_METERS

    accel_dist = AU_METERS
    decel_dist = max_ms_warp_speed / k_decel

    minimum_dist = accel_dist + decel_dist

    cruise_time = 0

    if minimum_dist > warp_dist:
        max_ms_warp_speed = warp_dist * k_accel * k_decel / (k_accel + k_decel)
    else:
        cruise_time = (warp_dist - minimum_dist) / max_ms_warp_speed

    accel_time = math.log(max_ms_warp_speed / k_accel) / k_accel
    decel_time = math.log(max_ms_warp_speed / warp_dropout_speed) / k_decel

    total_time = cruise_time + accel_time + decel_time
    return total_time


FitWarpTimeGraph.register()
