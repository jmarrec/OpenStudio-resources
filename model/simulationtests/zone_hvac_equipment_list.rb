# This test aims to test the ZoneHVACEquipmentList, especially with
# cooling/heating priorities set to 0 for some components
require 'openstudio'
require 'lib/baseline_model'


model = BaselineModel.new

#make a 1 story, 100m X 50m, 1 zone building
model.add_geometry({"length" => 100,
                    "width" => 50,
                    "num_floors" => 1,
                    "floor_to_floor_height" => 4,
                    "plenum_height" => 0,
                    "perimeter_zone_depth" => 0})

#add windows at a 40% window-to-wall ratio
model.add_windows({"wwr" => 0.4,
                  "offset" => 1,
                  "application_type" => "Above Floor"})

#add thermostats
model.add_thermostats({"heating_setpoint" => 19,
                       "cooling_setpoint" => 26})

#assign constructions from a local library to the walls/windows/etc. in the model
model.set_constructions()

#set whole building space type; simplified 90.1-2004 Large Office Whole Building
model.set_space_type()

#add design days to the model (Chicago)
model.add_design_days()

#add ASHRAE System type 01, PTHP, Residential
model.add_hvac({"ashrae_sys_num" => '02'})

# In order to produce more consistent results between different runs,
# we sort the zones by names
# (There's only one here, but just in case this would be copy pasted somewhere
# else...)
zones = model.getThermalZones.sort_by{|z| z.name.to_s}
z = zones[0]

# PTHP 1
pthp1 = z.equipment[0].to_ZoneHVACPackagedTerminalHeatPump.get
pthp1.setName("Cooling Only PTHP")
cc1 = pthp1.coolingCoil.to_CoilCoolingDXSingleSpeed.get
cc1.setName("#{pthp1.name.to_s} Autosized CoolingCoil")

hc1 = pthp1.heatingCoil.to_CoilHeatingDXSingleSpeed.get
hc1.setName("#{pthp1.name.to_s} Autosized HeatingCoil")

# Turn off backup coil
backup_hc1 = pthp1.supplementalHeatingCoil.to_CoilHeatingElectric.get
backup_hc1.setNominalCapacity(0.1)
backup_hc1.setAvailabilitySchedule(model.alwaysOffDiscreteSchedule)
backup_hc1.setName("#{pthp1.name.to_s} SupplHeatingCoil Off")

# Turn off OA
pthp1.setOutdoorAirFlowRateDuringCoolingOperation(0)
pthp1.setOutdoorAirFlowRateDuringHeatingOperation(0)
pthp1.setOutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded(0)

# Note: I would expect EnergyPlus to assume this one is turned off altogether
# for heating but it doesn't. So In OpenStudio currently if you use something
# below 1, it resets it to 1 (first in line)
z.setHeatingPriority(pthp1, 0)

# Baseboard
b = OpenStudio::Model::ZoneHVACBaseboardConvectiveElectric.new(model)
b.setName("Baseboard 100W")
b.setNominalCapacity(100)
b.addToThermalZone(z)

# PTHP 2
pthp2 = pthp1.clone(model).to_ZoneHVACPackagedTerminalHeatPump.get
pthp2.setName("Heating and Cooling PTHP")
pthp2.addToThermalZone(z)
z.setCoolingPriority(pthp2, 1)

cc2 = pthp2.coolingCoil.to_CoilCoolingDXSingleSpeed.get
cc2.setRatedTotalCoolingCapacity(100)
cc2.setName("#{pthp2.name.to_s} 100W CoolingCoil")

hc2 = pthp2.heatingCoil.to_CoilHeatingDXSingleSpeed.get
hc2.setRatedTotalHeatingCapacity(100)
hc2.setName("#{pthp2.name.to_s} 100W HeatingCoil")

# Turn off backup coil
backup_hc2 = pthp2.supplementalHeatingCoil.to_CoilHeatingElectric.get
backup_hc2.setNominalCapacity(0.2)
backup_hc2.setAvailabilitySchedule(model.alwaysOffDiscreteSchedule)
backup_hc2.setName("#{pthp2.name.to_s} SupplHeatingCoil Off")

# Turn off OA
pthp2.setOutdoorAirFlowRateDuringCoolingOperation(0)
pthp2.setOutdoorAirFlowRateDuringHeatingOperation(0)
pthp2.setOutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded(0)


z.setSequentialCoolingFraction(pthp1, 0.7)
z.setSequentialCoolingFraction(pthp2, 0.6)

# Add output variables?
add_out_vars = false
if add_out_vars
  vars = [
    "Zone Packaged Terminal Heat Pump Total Heating Rate",
    "Zone Packaged Terminal Heat Pump Total Cooling Rate",
    "Baseboard Total Heating Rate",
    "Baseboard Electric Power",
    "Cooling Coil Total Cooling Rate",
    "Cooling Coil Electric Power",
    "Heating Coil Heating Rate",
    "Heating Coil Electric Power",
    "Zone Mean Air Temperature",
  ]
  vars.each do |var|
    outvar = OpenStudio::Model::OutputVariable.new(var, model)
    outvar.setReportingFrequency("Detailed")
  end
end

#save the OpenStudio model (.osm)
model.save_openstudio_osm({"osm_save_directory" => Dir.pwd,
                           "osm_name" => "out.osm"})
