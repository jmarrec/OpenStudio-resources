import openstudio
from lib.baseline_model import BaselineModel

model = BaselineModel()

# make a 1 story, 100m X 50m, 1 zone building
model.add_geometry(length=100, width=50, num_floors=1, floor_to_floor_height=4, plenum_height=0, perimeter_zone_depth=0)

# add windows at a 40% window-to-wall ratio
model.add_windows(wwr=0.4, offset=1, application_type="Above Floor")

# add thermostats
model.add_thermostats(heating_setpoint=24, cooling_setpoint=28)

# assign constructions from a local library to the walls/windows/etc. in the model
model.set_constructions()

# set whole building space type; simplified 90.1-2004 Large Office Whole Building
model.set_space_type()

# add design days to the model (Chicago)
model.add_design_days()

# In order to produce more consistent results between different runs,
# we sort the zones by names (only one here anyways...)
zones = sorted(model.getThermalZones(), key=lambda z: z.nameString())
zone = zones[0]


USE_TWO_LOOPS = True
USE_OA_RESET = True
USE_ASHP_SPM_WHEN_ONE_LOOP = False



###############################################################################
#                       M A K E    S O M E    L O O P S                       #
###############################################################################

############### HEATING / COOLING (LOAD) LOOPS  ###############

hw_temp_f = 190
hw_delta_t_r = 20  # 20F delta-T
hw_temp_c = openstudio.convert(hw_temp_f, "F", "C").get()
hw_delta_t_k = openstudio.convert(hw_delta_t_r, "R", "K").get()

ashp_hw_temp_f = 140
ashp_hw_temp_c = openstudio.convert(ashp_hw_temp_f, "F", "C").get()

hw_loop = openstudio.model.PlantLoop(model)
hw_loop.setName("Hot Water Loop Air Source")
hw_loop.setMinimumLoopTemperature(10)

sizing_plant = hw_loop.sizingPlant()
sizing_plant.setLoopType("Heating")
sizing_plant.setDesignLoopExitTemperature(hw_temp_c)
sizing_plant.setLoopDesignTemperatureDifference(hw_delta_t_k)
# Pump
hw_pump = openstudio.model.PumpVariableSpeed(model)
hw_pump_head_ft_h2o = 60.0
hw_pump_head_press_pa = openstudio.convert(hw_pump_head_ft_h2o, "ftH_{2}O", "Pa").get()
hw_pump.setRatedPumpHead(hw_pump_head_press_pa)
hw_pump.setPumpControlType("Intermittent")
hw_pump.addToNode(hw_loop.supplyInletNode())

chw_loop = openstudio.model.PlantLoop(model)
chw_loop.setName("Chilled Water Loop Air Source")
chw_loop.setMaximumLoopTemperature(98)
chw_loop.setMinimumLoopTemperature(1)
chw_temp_f = 44
chw_delta_t_r = 10.1  # 10.1F delta-T
chw_temp_c = openstudio.convert(chw_temp_f, "F", "C").get()
chw_delta_t_k = openstudio.convert(chw_delta_t_r, "R", "K").get()
chw_temp_sch = openstudio.model.ScheduleRuleset(model)
chw_temp_sch.defaultDaySchedule().addValue(openstudio.Time(0, 24, 0, 0), chw_temp_c)
chw_stpt_manager = openstudio.model.SetpointManagerScheduled(model, chw_temp_sch)
chw_stpt_manager.addToNode(chw_loop.supplyOutletNode())
sizing_plant = chw_loop.sizingPlant()
sizing_plant.setLoopType("Cooling")
sizing_plant.setDesignLoopExitTemperature(chw_temp_c)
sizing_plant.setLoopDesignTemperatureDifference(chw_delta_t_k)
# Pump
pri_chw_pump = openstudio.model.HeaderedPumpsConstantSpeed(model)
pri_chw_pump.setName("Chilled Water Loop Primary Pump Air Source")
pri_chw_pump_head_ft_h2o = 15
pri_chw_pump_head_press_pa = openstudio.convert(pri_chw_pump_head_ft_h2o, "ftH_{2}O", "Pa").get()
pri_chw_pump.setRatedPumpHead(pri_chw_pump_head_press_pa)
pri_chw_pump.setMotorEfficiency(0.9)
pri_chw_pump.setPumpControlType("Intermittent")
pri_chw_pump.addToNode(chw_loop.supplyInletNode())


ashp_loop = None
if USE_TWO_LOOPS:
    ###############################################################################
    #                       A I R    S O U R C E    H P                         #
    ###############################################################################
    ashp_loop = openstudio.model.PlantLoop(model)
    ashp_loop.setName("ASHP Loop Air Source")
    sizing_plant = ashp_loop.sizingPlant()
    sizing_plant.setLoopType("Heating")
    sizing_plant.setDesignLoopExitTemperature(ashp_hw_temp_c)
    sizing_plant.setLoopDesignTemperatureDifference(hw_delta_t_k)
    # Pump
    hw_pump = openstudio.model.PumpVariableSpeed(model)
    hw_pump_head_ft_h2o = 60.0
    hw_pump_head_press_pa = openstudio.convert(hw_pump_head_ft_h2o, "ftH_{2}O", "Pa").get()
    hw_pump.setRatedPumpHead(hw_pump_head_press_pa)
    hw_pump.setPumpControlType("Intermittent")
    hw_pump.addToNode(ashp_loop.supplyInletNode())

###############################################################################
#                         A I R    S O U R C E    H P                         #
###############################################################################

# PlantLoopHeatPump_EIR_AirSource.idf

plhp_airsource_htg = openstudio.model.HeatPumpPlantLoopEIRHeating(model)
plhp_airsource_clg = openstudio.model.HeatPumpPlantLoopEIRCooling(model)

plhp_airsource_htg.setName("Heat Pump Plant Loop EIR Heating - AirSource")
plhp_airsource_htg.setCompanionCoolingHeatPump(plhp_airsource_clg)
# This is already the default, since it's not connected to any secondary plant loop
# plhp_airsource_htg.setCondenserType('AirSource')

# plhp_airsource_htg.setLoadSideReferenceFlowRate(0.005)
# plhp_airsource_htg.setSourceSideReferenceFlowRate(2.0)
# plhp_airsource_htg.setReferenceCapacity(80000)
plhp_airsource_htg.autosizeReferenceCapacity()
plhp_airsource_htg.autosizeSourceSideReferenceFlowRate()
plhp_airsource_htg.autosizeLoadSideReferenceFlowRate()

plhp_airsource_htg.setReferenceCoefficientofPerformance(4.5)
plhp_airsource_htg.setSizingFactor(1)
plhp_airsource_htg.capacityModifierFunctionofTemperatureCurve().setName("CapCurveFuncTemp Air Source")
plhp_airsource_htg.electricInputtoOutputRatioModifierFunctionofTemperatureCurve().setName("EIRCurveFuncTemp Air Source")
plhp_airsource_htg.electricInputtoOutputRatioModifierFunctionofPartLoadRatioCurve().setName(
    "EIRCurveFuncPLR Air Source"
)

plhp_airsource_clg.setName("Heat Pump Plant Loop EIR Cooling - AirSource")
plhp_airsource_clg.setCompanionHeatingHeatPump(plhp_airsource_htg)
# plhp_airsource_clg.setCondenserType('AirSource')

# plhp_airsource_clg.setLoadSideReferenceFlowRate(0.005)
# plhp_airsource_clg.setSourceSideReferenceFlowRate(20.0)
# plhp_airsource_clg.setReferenceCapacity(400000)
plhp_airsource_clg.autosizeReferenceCapacity()
plhp_airsource_clg.autosizeSourceSideReferenceFlowRate()
plhp_airsource_clg.autosizeLoadSideReferenceFlowRate()

plhp_airsource_clg.setReferenceCoefficientofPerformance(5.0)
plhp_airsource_clg.setSizingFactor(1)
plhp_airsource_clg.capacityModifierFunctionofTemperatureCurve().setName("CapCurveFuncTemp2 Air Source")
plhp_airsource_clg.electricInputtoOutputRatioModifierFunctionofTemperatureCurve().setName(
    "EIRCurveFuncTemp2 Air Source"
)
plhp_airsource_clg.electricInputtoOutputRatioModifierFunctionofPartLoadRatioCurve().setName(
    "EIRCurveFuncPLR2 Air Source"
)

plhp_airsource_htg.setHeatPumpSizingMethod("GreaterOfHeatingOrCooling")

if not USE_TWO_LOOPS:
    hw_loop.addSupplyBranchForComponent(plhp_airsource_htg)
chw_loop.addSupplyBranchForComponent(plhp_airsource_clg)


if USE_OA_RESET:
    spm_oa_reset = openstudio.model.SetpointManagerOutdoorAirReset(model)
    spm_oa_reset.setName("OA Reset for HW Loop Air Source")

    # 190 F at 19.4 F (oat_low) and 140 F at 65.1 F (oat_high)
    sp_at_oat_low = hw_temp_f # 190 F
    oat_low = 19.4
    sp_at_oat_high = 140
    oat_high = 65.0

    spm_oa_reset.setSetpointatOutdoorLowTemperature(hw_temp_c)

    spm_oa_reset.setControlVariable('Temperature')
    spm_oa_reset.setSetpointatOutdoorLowTemperature(openstudio.convert(sp_at_oat_low, 'F', 'C').get())
    spm_oa_reset.setOutdoorLowTemperature(openstudio.convert(oat_low, 'F', 'C').get())
    spm_oa_reset.setSetpointatOutdoorHighTemperature(openstudio.convert(sp_at_oat_high, 'F', 'C').get())
    spm_oa_reset.setOutdoorHighTemperature(openstudio.convert(oat_high, 'F', 'C').get())
    spm_oa_reset.addToNode(hw_loop.loopTemperatureSetpointNode())
else:
    hw_temp_sch = openstudio.model.ScheduleRuleset(model)
    hw_temp_sch.setName("HW Temp Schedule - 180F")
    hw_temp_sch.defaultDaySchedule().addValue(openstudio.Time(0, 24, 0, 0), hw_temp_c)
    hw_stpt_manager = openstudio.model.SetpointManagerScheduled(model, hw_temp_sch)
    hw_stpt_manager.addToNode(hw_loop.supplyOutletNode())

if USE_ASHP_SPM_WHEN_ONE_LOOP:
    ashp_hw_temp_sch = openstudio.model.ScheduleRuleset(model)
    ashp_hw_temp_sch.setName("ASHP HW Temp Schedule - 140F")
    ashp_hw_temp_sch.defaultDaySchedule().addValue(openstudio.Time(0, 24, 0, 0), ashp_hw_temp_c)
    ashp_hw_stpt_manager = openstudio.model.SetpointManagerScheduled(model, ashp_hw_temp_sch)
    ashp_hw_stpt_manager.addToNode(plhp_airsource_htg.loadSideWaterOutletNode().get())
elif USE_TWO_LOOPS:
    ashp_hw_temp_sch = openstudio.model.ScheduleRuleset(model)
    ashp_hw_temp_sch.setName("ASHP HW Temp Schedule - 140F")
    ashp_hw_temp_sch.defaultDaySchedule().addValue(openstudio.Time(0, 24, 0, 0), ashp_hw_temp_c)
    ashp_hw_stpt_manager = openstudio.model.SetpointManagerScheduled(model, ashp_hw_temp_sch)
    ashp_hw_stpt_manager.addToNode(ashp_loop.supplyOutletNode())

    hx = openstudio.model.HeatExchangerFluidToFluid(model)
    hx.setName("Heat Exchanger ASHP to HW Loop")
    hx.setControlType("HeatingSetpointModulated")

    ashp_loop.addSupplyBranchForComponent(plhp_airsource_htg)
    ashp_loop.addDemandBranchForComponent(hx)
    hw_loop.addSupplyBranchForComponent(hx)



# Maximum Supply Water Temperature Curve Name (function of outdoor dry-bulb temperature)
ashp_max_temp_curve = openstudio.model.CurveLinear(model)
ashp_max_temp_curve.setName(f"ASHP Max LWT Curve - {ashp_hw_temp_f} F")
ashp_max_temp_curve.setCoefficient1Constant(ashp_hw_temp_c)
ashp_max_temp_curve.setCoefficient2x(0.0)
ashp_max_temp_curve.setMinimumValueofx(-20.0)
ashp_max_temp_curve.setMaximumValueofx(50.0)
ashp_max_temp_curve.setInputUnitTypeforX("Temperature")
ashp_max_temp_curve.setOutputUnitType("Temperature")
plhp_airsource_htg.setMaximumSupplyWaterTemperatureCurve(ashp_max_temp_curve)


# Backup boiler

boiler = openstudio.model.BoilerHotWater(model)
hw_loop.addSupplyBranchForComponent(boiler)

hw_loop.setLoadDistributionScheme("SequentialLoad")

###############################################################

###############################################################################
#                            Z O N E    L E V E L                             #
###############################################################################

fourPipeFan = openstudio.model.FanOnOff(model, model.alwaysOnDiscreteSchedule())
fourPipeHeat = openstudio.model.CoilHeatingWater(model, model.alwaysOnDiscreteSchedule())
hw_loop.addDemandBranchForComponent(fourPipeHeat)
fourPipeCool = openstudio.model.CoilCoolingWater(model, model.alwaysOnDiscreteSchedule())
chw_loop.addDemandBranchForComponent(fourPipeCool)
fourPipeFanCoil = openstudio.model.ZoneHVACFourPipeFanCoil(
    model, model.alwaysOnDiscreteSchedule(), fourPipeFan, fourPipeCool, fourPipeHeat
)
fourPipeFanCoil.addToThermalZone(zone)


model.rename_loop_nodes()

model.outdoorAirNode()

avm_HTOff = openstudio.model.AvailabilityManagerHighTemperatureTurnOff(model)
avm_HTOff.setSensorNode(model.outdoorAirNode())
avm_HTOff.setTemperature(openstudio.convert(65.0, "F", "C").get())
hw_loop.addAvailabilityManager(avm_HTOff)

avm_LTOn = openstudio.model.AvailabilityManagerLowTemperatureTurnOn(model)
avm_LTOn.setSensorNode(model.outdoorAirNode())
avm_LTOn.setTemperature(openstudio.convert(60.0, "F", "C").get())
hw_loop.addAvailabilityManager(avm_LTOn)

if USE_TWO_LOOPS:
    ashp_loop.addAvailabilityManager(avm_HTOff)
    ashp_loop.addAvailabilityManager(avm_LTOn)

# Chw
# Get the chiller water loop
# We turn it off if the OA Temp is below 15C, turn if back on if its over 18C
avm_LTOff = openstudio.model.AvailabilityManagerLowTemperatureTurnOff(model)
avm_LTOff.setSensorNode(model.outdoorAirNode())
avm_LTOff.setTemperature(openstudio.convert(60.0, "F", "C").get())
chw_loop.addAvailabilityManager(avm_LTOff)

avm_HTOn = openstudio.model.AvailabilityManagerHighTemperatureTurnOn(model)
avm_HTOn.setSensorNode(model.outdoorAirNode())
avm_HTOn.setTemperature(openstudio.convert(65.0, "F", "C").get())
chw_loop.addAvailabilityManager(avm_HTOn)



add_out_vars = True
if add_out_vars:
    # Request timeseries data for debugging
    reporting_frequency = "Timestep"

    out_vars = [
        "Boiler Heating Rate",
        "Boiler Inlet Temperature",
        "Boiler Mass Flow Rate",
        "Boiler Outlet Temperature",
        "Boiler Part Load Ratio",
        "Heat Pump Cycling Ratio",
        "Heat Pump Load Side Heat Transfer Rate",
        "Heat Pump Load Side Inlet Temperature",
        "Heat Pump Load Side Mass Flow Rate",
        "Heat Pump Load Side Outlet Temperature",
        "Heat Pump Part Load Ratio",
        "Plant Supply Side Cooling Demand Rate",
        "Plant Supply Side Heating Demand Rate",
        "Plant Supply Side Inlet Temperature",
        "Plant Supply Side Not Distributed Demand Rate",
        "Plant Supply Side Outlet Temperature",
        "Site Outdoor Air Drybulb Temperature"
    ]

    # Enable all output Variables for the object
    for var_name in out_vars:
        outputVariable = openstudio.model.OutputVariable(var_name, model)
        outputVariable.setReportingFrequency(reporting_frequency)

    node_vars = ["System Node Setpoint Temperature", "System Node Temperature", "System Node Mass Flow Rate"]
    for node_var in node_vars:
        outputVariable = openstudio.model.OutputVariable(node_var, model)
        outputVariable.setReportingFrequency(reporting_frequency)
        outputVariable.setKeyValue(hw_loop.loopTemperatureSetpointNode().nameString())

# save the OpenStudio model (.osm)
model.save_openstudio_osm(osm_save_directory=None, osm_name="in.osm")
