# Note JM 2018-11-08
# This test aims to test for OpenStudio issue #3332
# I think this is an E+ bug that isn't caught yet because you need two things:
# * A ZoneHVAC:WaterToAir with Variable Speed coils
# * An unitary system with Variable Speed coils so that it produces at least
# one UnitarySystemPerformance:Multispeed

require 'openstudio'
require 'lib/baseline_model'

model = BaselineModel.new

#make a 2 story, 100m X 50m, 2 zones building
model.add_geometry({"length" => 100,
              "width" => 50,
              "num_floors" => 2,
              "floor_to_floor_height" => 4,
              "plenum_height" => 1,
              "perimeter_zone_depth" => 0})

#add windows at a 40% window-to-wall ratio
model.add_windows({"wwr" => 0.4,
                  "offset" => 1,
                  "application_type" => "Above Floor"})

#add thermostats
model.add_thermostats({"heating_setpoint" => 24,
                      "cooling_setpoint" => 28})

#assign constructions from a local library to the walls/windows/etc. in the model
model.set_constructions()

#set whole building space type; simplified 90.1-2004 Large Office Whole Building
model.set_space_type()

#add design days to the model (Chicago)
model.add_design_days()

alwaysOn = model.alwaysOnDiscreteSchedule()

# Condenser System
condenserSystem = OpenStudio::Model::PlantLoop.new(model)
sizingPlant = condenserSystem.sizingPlant()
sizingPlant.setLoopType("Condenser")
sizingPlant.setDesignLoopExitTemperature(29.4)
sizingPlant.setLoopDesignTemperatureDifference(5.6)

distHeating = OpenStudio::Model::DistrictHeating.new(model)
condenserSystem.addSupplyBranchForComponent(distHeating)

distCooling = OpenStudio::Model::DistrictCooling.new(model)
condenserSystem.addSupplyBranchForComponent(distCooling)

condenserSupplyOutletNode = condenserSystem.supplyOutletNode()
condenserSupplyInletNode = condenserSystem.supplyInletNode()

pump3 = OpenStudio::Model::PumpVariableSpeed.new(model)
pump3.addToNode(condenserSupplyInletNode)

spm = OpenStudio::Model::SetpointManagerFollowOutdoorAirTemperature.new(model)
spm.addToNode(condenserSupplyOutletNode)

# In order to produce more consistent results between different runs,
# we sort the zones by names
zones = model.getThermalZones.sort_by{|z| z.name.to_s}

# Unitary System test
# Make it a unitary with 3 speed cooling coil and 3 speed heating coil
unitary_zone = zones[0]

airLoop_1 = OpenStudio::Model::AirLoopHVAC.new(model)
airLoop_1_supplyNode = airLoop_1.supplyOutletNode()

unitary_1 = OpenStudio::Model::AirLoopHVACUnitarySystem.new(model)
unitary_1.setName("UnitarySys")
fan_1 = OpenStudio::Model::FanConstantVolume.new(model, alwaysOn)
fan_1.setName("#{unitary_1.name.to_s} Fan")

cooling_coil_1 = OpenStudio::Model::CoilCoolingWaterToAirHeatPumpVariableSpeedEquationFit.new(model)
cooling_coil_1.setName("#{unitary_1.name.to_s} Cooling Coil")
speedData = OpenStudio::Model::CoilCoolingWaterToAirHeatPumpVariableSpeedEquationFitSpeedData.new(model)
cooling_coil_1.addSpeed(speedData)
speedData = OpenStudio::Model::CoilCoolingWaterToAirHeatPumpVariableSpeedEquationFitSpeedData.new(model)
cooling_coil_1.addSpeed(speedData)
#speedData = OpenStudio::Model::CoilCoolingWaterToAirHeatPumpVariableSpeedEquationFitSpeedData.new(model)
#cooling_coil_1.addSpeed(speedData)

heating_coil_1 = OpenStudio::Model::CoilHeatingWaterToAirHeatPumpVariableSpeedEquationFit.new(model)
heating_coil_1.setName("#{unitary_1.name.to_s} Heating Coil")
speedData = OpenStudio::Model::CoilHeatingWaterToAirHeatPumpVariableSpeedEquationFitSpeedData.new(model)
heating_coil_1.addSpeed(speedData)
speedData = OpenStudio::Model::CoilHeatingWaterToAirHeatPumpVariableSpeedEquationFitSpeedData.new(model)
heating_coil_1.addSpeed(speedData)
#speedData = OpenStudio::Model::CoilHeatingWaterToAirHeatPumpVariableSpeedEquationFitSpeedData.new(model)
#heating_coil_1.addSpeed(speedData)


unitary_1.setControllingZoneorThermostatLocation(unitary_zone)
unitary_1.setFanPlacement("BlowThrough")
unitary_1.setSupplyAirFanOperatingModeSchedule(alwaysOn)
unitary_1.setSupplyFan(fan_1)
unitary_1.setCoolingCoil(cooling_coil_1)
unitary_1.setHeatingCoil(heating_coil_1)

condenserSystem.addDemandBranchForComponent(heating_coil_1)
condenserSystem.addDemandBranchForComponent(cooling_coil_1)

unitary_1.addToNode(airLoop_1_supplyNode)

air_terminal_1 = OpenStudio::Model::AirTerminalSingleDuctUncontrolled.new(model, alwaysOn)
air_terminal_1.setName("#{unitary_1.name.to_s} ATU")
airLoop_1.addBranchForZone(unitary_zone, air_terminal_1)


# Now we need a ZoneHVACWaterToAirHeatPump
# Make it a two speed cooling and two speed heating
wahp_zone = zones[0]
wahp_name = "Zone WAHP"
supplyFan = OpenStudio::Model::FanOnOff.new(model)
supplyFan.setName("#{wahp_name} Fan")

wahpDXCC = OpenStudio::Model::CoilCoolingWaterToAirHeatPumpVariableSpeedEquationFit.new(model)
wahpDXCC.setName("#{wahp_name} Cooling Coil")
3.times do |_|
  speedData = OpenStudio::Model::CoilCoolingWaterToAirHeatPumpVariableSpeedEquationFitSpeedData.new(model)
  wahpDXCC.addSpeed(speedData)
end

wahpDXHC = OpenStudio::Model::CoilHeatingWaterToAirHeatPumpVariableSpeedEquationFit.new(model)
speedData = OpenStudio::Model::CoilHeatingWaterToAirHeatPumpVariableSpeedEquationFitSpeedData.new(model)
wahpDXHC.setName("#{wahp_name} Heating Coil")
3.times do |_|
  speedData = OpenStudio::Model::CoilHeatingWaterToAirHeatPumpVariableSpeedEquationFitSpeedData.new(model)
  wahpDXHC.addSpeed(speedData)
end

supplementalHC = OpenStudio::Model::CoilHeatingElectric.new(model, alwaysOn)
supplementalHC.setName("#{wahp_name} Suppl Heating Coil")

wahp = OpenStudio::Model::ZoneHVACWaterToAirHeatPump.new(model, alwaysOn,
                                                         supplyFan,
                                                         wahpDXHC,
                                                         wahpDXCC,
                                                         supplementalHC)
wahp.setName(wahp_name)
wahp.addToThermalZone(wahp_zone);

condenserSystem.addDemandBranchForComponent(wahpDXHC)
condenserSystem.addDemandBranchForComponent(wahpDXCC)

#save the OpenStudio model (.osm)
model.save_openstudio_osm({"osm_save_directory" => Dir.pwd,
                           "osm_name" => "in.osm"})

