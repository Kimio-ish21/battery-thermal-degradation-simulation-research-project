import numpy as np


np.random.seed(42) 

standby_kw = (5.0, 9.0)   
standby_hrs = (15.0, 16.0)  
oper_kw = (8.0, 16.0)   
oper_hrs = (8.0, 9.0)   

simulations =10000   
base_life_years =20      # Standard Power Purchase Agreement lifespan
energy_cost_kwh_mean =0.12  
energy_cost_kwh_std =0.01    
battery_replacement_cost_per_kwh = 200.00   #  NEED TO VALIDATE WITH PAPER DATA
total_capacity_kwh =5000   

baseline_k = 1.2   
baseline_temp_c =25.0  #Optimal operating temperature for Li-ion cells


soils = [
    {"name": "Unit 741B: Oakville Fine Sand", "k_value": 0.6},
    {"name": "Unit 201A: Gilford Sandy Loam", "k_value": 0.9},
    {"name": "Unit 103A: Houghton Muck", "k_value": 1.0},
    {"name": "Unit 318A: Lorenzo Loam", "k_value": 1.1},
    {"name": "Unit 146A: Elliott Silt Loam", "k_value": 1.2},
    {"name": "Unit 27B: Miami Silt Loam", "k_value": 1.2},
    {"name": "Unit 805B: Orthents Clayey", "k_value": 1.5},
    {"name": "Unit 232A: Ashkum Silty Clay", "k_value": 1.5},
]

def calculate_arrhenius_degradation(temp_celsius, time_years):
    activation_energy = 40000   #NEED TO VALIDATE WITH PAPER DATA
    gas_constant = 8.314
    pre_exponential = 23886.0   # https://www.sciencedirect.com/science/article/abs/pii/S0378775310021269
    effective_temp_c = np.minimum(temp_celsius, 35.0) #https://pubs.acs.org/doi/10.1021/acs.jpcc.2c02396
    temp_kelvin = effective_temp_c + 273.15

    time_days = time_years * 365

    degradation_rate = pre_exponential * np.exp(-activation_energy / (gas_constant * temp_kelvin))
    capacity_lost = degradation_rate * np.sqrt(time_days)
    # Physical ceiling 
    return np.minimum(capacity_lost, 1.0)


def run_simulation(soil_name, k_value):
    print(f"{soil_name} (k={k_value})")

    for reliance in [0.3, 0.5, 0.7]: # how much harder the HVAC works on this soil vs. the baseline soil?
        load_multiplier = (1.0 - reliance) + reliance * (baseline_k / k_value)
        thermal_delta = 10.0 * (baseline_k / k_value - 1.0) * reliance
        operating_temp = np.maximum(baseline_temp_c,baseline_temp_c +thermal_delta)
        print(f"\nReliance {reliance:.0%} - Load Multiplier: {load_multiplier:.2f} - Operating Temp: {operating_temp:.1f} °C")

        stochastic_temp_arr= np.random.normal(operating_temp, 2.0, simulations)

        standby_kw_arr =np.random.uniform(standby_kw[0], standby_kw[1],simulations)
        standby_hrs_arr = np.random.uniform(standby_hrs[0],standby_hrs[1], simulations)
        oper_kw_arr = np.random.uniform(oper_kw[0], oper_kw[1],simulations)
        oper_hrs_arr= np.random.uniform(oper_hrs[0],oper_hrs[1], simulations)

        daily_thermal_kwh= (standby_kw_arr * standby_hrs_arr) +(oper_kw_arr *oper_hrs_arr)
        actual_annual_load = (daily_thermal_kwh * 365)* load_multiplier
        energy_price =np.random.normal(energy_cost_kwh_mean, energy_cost_kwh_std, simulations)
        total_energy_cost =actual_annual_load*energy_price* base_life_years
        fade_pct = calculate_arrhenius_degradation(stochastic_temp_arr,base_life_years)
        kwh_destroyed =fade_pct *total_capacity_kwh
        degradation_cost =kwh_destroyed * battery_replacement_cost_per_kwh
        tco_array = total_energy_cost + degradation_cost # HVAC cost + degradation cost


        fade_med = np.median(fade_pct)
        fade_p95 = np.percentile(fade_pct,95)
        kwh_med = np.median(kwh_destroyed)
        kwh_p95= np.percentile(kwh_destroyed,95)
        deg_med = np.median(degradation_cost)
        deg_p95 =np.percentile(degradation_cost,95)



        print(f"\nAt {reliance:.0%} Reliance:")
        print(f"HVAC Multiplier: {load_multiplier:.2f}x")
        print(f"Internal Operating Temp: {operating_temp:.2f} C")

        print(f"20-Year Capacity Loss: Median {fade_med*100:.2f}% 95th {fade_p95*100:.2f}% "
              f"({kwh_med:.1f} kWh median, {kwh_p95:.1f} kWh 95th)")
        print(f"Cost of HVAC (OpEx): Median ${np.median(total_energy_cost):,.2f} Min ${np.min(total_energy_cost):,.2f} Max ${np.max(total_energy_cost):,.2f}")
        print(f"Cost of Capacity Loss: Median ${deg_med:,.2f} 95th ${deg_p95:,.2f}")
        print(f"Total 20-Year TCO: Median ${np.median(tco_array):,.2f} 95th Percentile ${np.percentile(tco_array, 95):,.2f}")

for soil in soils:
    run_simulation(soil["name"], soil["k_value"])
