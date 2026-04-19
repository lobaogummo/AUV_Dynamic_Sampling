from scipy.io import netcdf #python -m pip install scipy
import numpy as np
import matplotlib   #pip install matplotlib
import matplotlib.pyplot as plt #pip install matplotlib
import  matplotlib.patches
import xarray as xr #python -m pip install xarray
import scipy.spatial.distance 
import scipy.spatial 
import geopy.distance   #pip install geopy
import datetime
import sys
import scipy.ndimage
from scipy.interpolate import griddata
from Utils import *
from Config_file import *

from pyvrp import Model, read   #pip install pyvrp
from pyvrp.stop import MaxIterations, MaxRuntime, NoImprovement
from pyvrp import CostEvaluator, Route, Solution, VehicleType, PenaltyManager

#RUN
# python3.12 /folder_path/OptimalPlanning.py <file_name.nc>


def _plot_base_map(arr, title, cmap_name="viridis"):
    # Visual-only helper: invalid cells stay visually separate (white) from low values.
    arr_plot = np.asarray(arr, dtype=np.float64).copy()
    arr_plot[~np.isfinite(arr_plot)] = np.nan
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(color="white")
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    im = ax.imshow(arr_plot, interpolation="none", cmap=cmap, origin="lower")
    ax.grid()
    fig.colorbar(im, ax=ax)
    ax.set_title(title)
    fig.tight_layout()
    return fig, ax

#################################################    PRE PROCESSING MODEL 2   #################################################
if MODEL_HOPS == False:
    netcdf_model = xr.open_dataset('model2_31_10_2024.nc', decode_times=False)  #insert name of model 2 .nc file and run the algorithm: python3.12 /folder_path/OptimalPlanning.py <file_name_model_hops.nc>
    netcdf_model.STDto40m.plot()
    plt.title('Model Input STD40m')
    plt.show()

    LAT = netcdf_model.LAT.to_numpy()
    LON = netcdf_model.LON.to_numpy()
    STD = netcdf_model.STDto40m.to_numpy()

    dist_lat_axis = geopy.distance.geodesic([min(LAT), min(LON)], [max(LAT), min(LON)]).m
    dist_lon_axis = geopy.distance.geodesic([min(LAT), min(LON)], [min(LAT), max(LON)]).m

    number_lat = dist_lat_axis/HOPS_GRID_RESOLUTION
    number_lon = dist_lon_axis/HOPS_GRID_RESOLUTION

    #Grid interpolation to obtain HOPS Model grid resolution
    points_coords = []
    points_values = []
    for i in range(len(LAT)):
        for j in range(len(LON)):
            point_c = [i, j]
            point_v = STD[i,j]
            points_coords.append(point_c)
            points_values.append(point_v)

    points_coords = np.array(points_coords)
    points_values = np.array(points_values)

    cell_lat_res = len(LAT)/number_lat
    cell_lon_res = len(LON)/number_lon

    grid_lat, grid_lon = np.mgrid[0:len(LAT):cell_lat_res, 0:len(LON):cell_lon_res]

    new_std = griddata(points_coords, points_values, (grid_lat, grid_lon), method='linear')
    new_lat = np.linspace(min(LAT), max(LAT), np.shape(grid_lat)[0])
    new_lon = np.linspace(min(LON), max(LON), np.shape(grid_lat)[1])

    plt.imshow(new_std, origin='lower')
    plt.title('Interpolated')
    plt.show()

    #Cut the Area to obtain HOPS Area
    HOPS_LL_CORNER = [39.20198, -10.02656]
    HOPS_UR_CORNER = [39.89801, -8.90343]
    
    la_start = next(x for x, val in enumerate(new_lat) if val > HOPS_LL_CORNER[0])
    la_stop = next(x for x, val in enumerate(new_lat) if val > HOPS_UR_CORNER[0]) - 1
    lo_start = next(x for x, val in enumerate(new_lon) if val > HOPS_LL_CORNER[1])
    lo_stop = next(x for x, val in enumerate(new_lon) if val > HOPS_UR_CORNER[1]) - 1

    new_std = new_std[la_start:la_stop+2, lo_start:lo_stop+2]   
    new_lat = new_lat[la_start:la_stop+2]
    new_lon = new_lon[lo_start:lo_stop+2]

    #Replace nan values with -inf
    new_std[np.isnan(new_std)] = -np.inf  

    plt.imshow(new_std, origin='lower')
    plt.title('HOPS Area')
    plt.show()

    #Filter applied to the data
    sigma = [3, 3]                  
    new_std = scipy.ndimage.filters.gaussian_filter(new_std, sigma, mode='reflect')   

    plt.imshow(new_std, origin='lower')
    plt.title('Gaussian Filter')
    plt.show()

##################################################################################################################################
#################################################    STEP 0) READ HOPS.nc FILE   #################################################
##################################################################################################################################
if(len(sys.argv) != 2):
    print("Usage: python3 OptimalPlanningFRESNEL <file_name.nc>")
    sys.exit(1)

print("*** Read File ***")
file_name = sys.argv[1]
netcdf_file = xr.open_dataset(file_name, decode_times=False)

if MODEL_HOPS == False: 
    temperr2d = new_std 
else:
    temperr2d = netcdf_file.temperr.to_numpy()              #for the surface level
    #temperr2d = netcdf_file.temperrMean.to_numpy()         #for the mean value

latitude = netcdf_file.lat.to_numpy()   
longitude = netcdf_file.lon.to_numpy()
tbath = netcdf_file.tbath.to_numpy()                        
land_mask = netcdf_file.landt.to_numpy()                    

###########################################################################################################################
###############################################     STEP 1) INSERT MASKS    ###############################################
###########################################################################################################################
print("*** Insert Masks ***")
#temperr - Land-Sea mask total area (just for Plot)
temperr2d_masked = temperr2d.copy()
for i in range(land_mask.shape[0]):         
    for j in range(land_mask.shape[1]):
        if land_mask[i,j]==0:
            temperr2d_masked[i,j] = -np.inf


#tbath - Land-Sea mask total area (just for Plot)
tbath_masked = tbath.copy()
for i in range(land_mask.shape[0]):         
    for j in range(land_mask.shape[1]):
        if land_mask[i,j]==0:
            tbath_masked[i,j] = -np.inf


#Operation mask (crop the grid to the operational area only)
lat_start = next(x for x, val in enumerate(latitude) if val > OPERATION_LL_CORNER[0])
lat_stop = next(x for x, val in enumerate(latitude) if val > OPERATION_UR_CORNER[0]) - 1
lon_start = next(x for x, val in enumerate(longitude) if val > OPERATION_LL_CORNER[1])
lon_stop = next(x for x, val in enumerate(longitude) if val > OPERATION_UR_CORNER[1]) - 1

 
temperr2d_op = temperr2d[lat_start:lat_stop, lon_start:lon_stop]
tbath_op = tbath[lat_start:lat_stop, lon_start:lon_stop]
land_mask_op = land_mask[lat_start:lat_stop, lon_start:lon_stop]
latitude_op = latitude[lat_start:lat_stop]
longitude_op = longitude[lon_start:lon_stop]


"""# !!Very expensive step!!To RUN just if DISTANCE_FROM_LAND need to be changed (mask the points with a distance from land less than DISTANCE_FROM_LAND)
#Land-Sea mask
for i in range(land_mask_op.shape[0]):         
    for j in range(land_mask_op.shape[1]):
        if land_mask_op[i,j]==0:
            temperr2d_op[i,j] = -np.inf

#Distance from land mask
for i in range(land_mask_op.shape[0]):
    for j in range(land_mask_op.shape[1]):
        if(land_mask_op[i,j] == 0):
            for k in range(temperr2d_op.shape[0]):
                for l in range(temperr2d_op.shape[1]):
                    if(math.isinf(temperr2d_op[k,l]) == False):
                        land = [latitude_op[i], longitude_op[j]]
                        point = [latitude_op[k], longitude_op[l]]
                        if(geopy.distance.geodesic(point, land).km < DISTANCE_FROM_LAND):
                            temperr2d_op[k,l] = -np.inf  
np.save('temperr_MODEL_distanceFromLandMask5KMFilter23.npy',temperr2d_op) #Save map

if MODEL_HOPS == False:
    #temperr2d_op = np.load('temperr_MODEL_distanceFromLandMask5KM.npy')
    temperr2d_op = np.load('temperr_MODEL_distanceFromLandMask5KMFilter23.npy')
else: 
    temperr2d_op = np.load('temperr_op_distanceFromLandMask5KM.npy')
"""

#Bathymetric mask (mask the points with a depth less than MINIMUM_DEPTH)
for i in range(tbath_op.shape[0]):            
    for j in range(tbath_op.shape[1]):
        if tbath_op[i,j] > -MINIMUM_DEPTH:
            temperr2d_op[i,j] = -np.inf   


#Obstacles mask 
for idx in range(len(OBJECTS_LL_CORNER)):

    lat_obj_start = next(x for x, val in enumerate(latitude_op) if val > OBJECTS_LL_CORNER[idx][0])-1
    lat_obj_stop = next(x for x, val in enumerate(latitude_op) if val > OBJECTS_UR_CORNER[idx][0])
    lon_obj_start = next(x for x, val in enumerate(longitude_op) if val > OBJECTS_LL_CORNER[idx][1]) -1
    lon_obj_stop = next(x for x, val in enumerate(longitude_op) if val > OBJECTS_UR_CORNER[idx][1]) 

    latitude_obj = np.arange(lat_obj_start, lat_obj_stop + 1, 1).tolist()
    longitude_obj = np.arange(lon_obj_start, lon_obj_stop + 1, 1).tolist()

    #for line obstacles
    if(abs(lat_obj_start - lat_obj_stop) <= 1): latitude_obj = [lat_obj_start, lat_obj_start]
    if(abs(lon_obj_start - lon_obj_stop) <= 1): longitude_obj = [lon_obj_start, lon_obj_start]

    for i in range(temperr2d_op.shape[0]):      #lat        
        for j in range(temperr2d_op.shape[1]):  #lon
            if (i in latitude_obj and j in longitude_obj):
                temperr2d_op[i,j] = -np.inf

#PLOTS: for analysis before proceeding with the optimization
#area with temperr profile 
fig, ax = _plot_base_map(temperr2d_masked, 'Temperature error - HOPS Area - land mask', cmap_name='viridis')
plt.show()
plt.close(fig)


#Operation area with all masks
fig, ax = _plot_base_map(temperr2d_op, 'Temperature error - Operational Area - all masks', cmap_name='viridis')
plt.show()
plt.close(fig)

###########################################################################################################################
###############################################   STEP 2)  POINTS SELECTION    ############################################
###########################################################################################################################
print("*** Point Selection ***")

#Get contours level
max_level = temperr2d_op.max()
min_level = np.nanmin(temperr2d_op[temperr2d_op != -np.inf])
gap = max_level - min_level
step_level = gap / N_LEVELS

contour_points_lat, contour_points_lon, contour_points_level, levels = get_contour_levels(temperr2d_op, max_level, min_level, step_level)

contour_points = []
for i in range(len(contour_points_lat)):
    point = [contour_points_lat[i], contour_points_lon[i]]
    contour_points.append(point)

#Get spaced points on contour level
uncertain_points, uncertain_points_coord, uncertain_point_level_cl = find_POI_on_contour_levels(D_MIN_CONTOUR, contour_points_lat, contour_points_lon, contour_points_level, latitude_op, longitude_op)

#Get interior points using Voronoi
UNC_TRESHOLD_1 = min_level + (gap/N_LEVELS) #Not voronoi inside last contour level
UNC_TRESHOLD_2 = min_level + (gap/2)  

uncertain_points, uncertain_points_coord = additional_POI_inside_contour_levels(D_MIN_VORONOI, UNC_TRESHOLD_1, temperr2d_op, uncertain_points, uncertain_points_coord, latitude_op, longitude_op)
uncertain_points, uncertain_points_coord = additional_POI_inside_contour_levels(D_MIN_VORONOI, UNC_TRESHOLD_2, temperr2d_op, uncertain_points, uncertain_points_coord, latitude_op, longitude_op)


#PLOT: Operation area with all masks and uncertain points
fig, ax = _plot_base_map(temperr2d_op, 'Point Selection', cmap_name='viridis')
uncertain_points_for_scatter = [(y, x)  for x, y in uncertain_points]
ax.scatter(*zip(*uncertain_points_for_scatter), s=5, c='black', marker='o')
plt.show()
plt.close(fig)

#####################################################################################################################################
########################################         STEP 3)   VRP - Vehicle Routing Problem     ########################################
############################################ PyVRP: A High-Performance VRP Solver Package   #########################################
##################################### https://pubsonline.informs.org/doi/10.1287/ijoc.2023.0055   ###################################
print("*** VRP Solver (Node number estimation - "+str(STOP_RUN_TIME)+" [s]) ***")


# Add depots (starting points, ending points) to vrp nodes
vrp_nodes = uncertain_points
depots = get_depots(STARTING_POINTS, ENDING_POINTS, latitude_op, longitude_op)
vrp_nodes = remove_duplicates(depots, vrp_nodes)           #remove duplicate nodes (if a depot coincide with a node)
for node in depots[::-1]:                                   
    vrp_nodes = [node] + vrp_nodes

#Get nodes coords
vrp_nodes_coord = []
for node in vrp_nodes:  
    point_lat_lon = [latitude_op[node[0]], longitude_op[node[1]]]
    vrp_nodes_coord.append(point_lat_lon)  

#Get nodes prizes (prize obtained for visiting the client)
node_prices = get_nodes_prize(temperr2d_op, vrp_nodes, N_DEPOT)

#Get nodes distances (penalised distance where obstacles are present)
node_distances = get_nodes_distance(temperr2d_op, vrp_nodes)

################################################
# VRP Solver first time: estimate number of visited clients 
################################################

#Create instance for VRP problem    
mission_duration_s = []
for dur in MISSION_DURATIONS:
    mission_duration_s.append(from_hour_to_sec(dur))
create_vrp_problem_instance_file('VRP_instance_problem.vrp', vrp_nodes, node_distances, node_prices, AUV_NUMBER, N_DEPOT, mission_duration_s)

#Read instance 
instance = read("VRP_instance_problem.vrp", round_func="round") 

vehicles_max_distance = get_max_distances(mission_duration_s)

#Create instance
if(AUV_NUMBER == 1):
    instance = instance.replace(vehicle_types=[VehicleType(1, capacity=[0], start_depot=0, end_depot= 1, max_distance=vehicles_max_distance[0])])

elif(AUV_NUMBER == 2):
    instance = instance.replace(vehicle_types=[
                VehicleType(1, capacity=[0], start_depot=0, end_depot= 2, max_distance=vehicles_max_distance[0]),
                VehicleType(1, capacity=[0], start_depot=1, end_depot= 3, max_distance=vehicles_max_distance[1]),
                ])
    
elif(AUV_NUMBER == 3):
    instance = instance.replace(vehicle_types=[
                VehicleType(1, capacity=[0], start_depot=0, end_depot= 3, max_distance=vehicles_max_distance[0]),
                VehicleType(1, capacity=[0], start_depot=1, end_depot= 4, max_distance=vehicles_max_distance[1]),
                VehicleType(1, capacity=[0], start_depot=2, end_depot= 5, max_distance=vehicles_max_distance[2]),
                ])

#Create the VRP model
m = Model.from_data(instance)

#Solve the model
vrp_result = m.solve(stop=MaxRuntime(STOP_RUN_TIME), seed=SEED, display=True)  

#Get solution
vrp_routes_points, vrp_routes_points_coord = get_routes(vrp_result.best.routes(), vrp_nodes, vrp_nodes_coord)

#Routes analysis
vrp_routes_all_grid_points = get_all_routes_grid_points(vrp_routes_points)

vrp_routes_minimum_depth = get_routes_minimum_depth(tbath_op, vrp_routes_all_grid_points)

routes_length = get_routes_length(vrp_routes_points_coord)

total_prize = get_routes_prize(temperr2d_op, vrp_routes_all_grid_points)

vrp_routes_points_coord_and_depth = add_depth_info(tbath_op, vrp_routes_points, vrp_routes_points_coord)    

create_routes_file('routes_file_node_estimation.txt', vrp_routes_points_coord_and_depth, routes_length, vrp_routes_minimum_depth)  #Save routes (just debug)

################################################################
# VRP Solver second time: final routes 
################################################################
print("*** VRP Solver (Final routes) ***")

vrp_routes_waiting_time = get_routes_wp_waiting_time(vrp_routes_points, WP_WAITING_TIME)    #total amount of waypoints waiting time [seconds]
effective_travel_duration = get_effective_travel_duration(vrp_routes_waiting_time, mission_duration_s)
vehicles_max_distance_wt = get_max_distances(effective_travel_duration)

#Create new instance for VRP problem replacing the old one with updated max distances
if(AUV_NUMBER == 1):
    instance_wt = instance.replace(vehicle_types= [VehicleType(1, capacity=[0], start_depot=0, end_depot= 1, max_distance=vehicles_max_distance_wt[0])])

elif(AUV_NUMBER == 2):  
    instance_wt = instance.replace(vehicle_types=[  
                VehicleType(1, capacity=[0], start_depot=0, end_depot= 2, max_distance=vehicles_max_distance_wt[0]),
                VehicleType(1, capacity=[0], start_depot=1, end_depot= 3, max_distance=vehicles_max_distance_wt[1]),
                ])
    
elif(AUV_NUMBER == 3):  
    instance_wt = instance.replace(vehicle_types=[  
                VehicleType(1, capacity=[0], start_depot=0, end_depot= 3, max_distance=vehicles_max_distance_wt[0]),
                VehicleType(1, capacity=[0], start_depot=1, end_depot= 4, max_distance=vehicles_max_distance_wt[1]),
                VehicleType(1, capacity=[0], start_depot=2, end_depot= 5, max_distance=vehicles_max_distance_wt[2]),
                ])           

#Create the VRP model
m_wt = Model.from_data(instance_wt)

#Solve the model
no_imp = int(500*STOP_NO_ITER)
vrp_result_wt = m_wt.solve(stop=NoImprovement(no_imp), seed=SEED, display=True) 

#Get solution
vrp_routes_points_wt, vrp_routes_points_coord_wt = get_routes(vrp_result_wt.best.routes(), vrp_nodes, vrp_nodes_coord)

################################################################
#Routes analysis
################################################################
vrp_routes_all_grid_points_wt = get_all_routes_grid_points(vrp_routes_points_wt)    

vrp_routes_minimum_depth_wt = get_routes_minimum_depth(tbath_op, vrp_routes_all_grid_points_wt) 

total_wp_prize_wt = get_routes_prize(temperr2d_op, vrp_routes_points_wt)     

total_prize_wt = get_routes_prize(temperr2d_op,vrp_routes_all_grid_points_wt)   

routes_length_wt = get_routes_length(vrp_routes_points_coord_wt)    

vrp_routes_points_coord_and_depth_wt = add_depth_info(tbath_op, vrp_routes_points_wt, vrp_routes_points_coord_wt) 

routes_waiting_time = get_routes_wp_waiting_time(vrp_routes_points_wt, WP_WAITING_TIME) 

print("Total WP Routes Temperr [°C]:")
print(total_wp_prize_wt)
print("Total All Routes Temperr [°C]:")
print(total_prize_wt)

###############################################  SAVE FINAL ROUTES  ##############################################################
if CLEAN_ROUTE:
    #clean the route
    vrp_routes_points_wt_clean, vrp_routes_points_coord_wt_clean = delete_redundant_wp(temperr2d_op, vrp_routes_points_wt, vrp_routes_points_coord_wt)
else:
    vrp_routes_points_wt_clean, vrp_routes_points_coord_wt_clean = vrp_routes_points_wt, vrp_routes_points_coord_wt

#compute the waiting time with the cleaned/or not wp
routes_waiting_time_clean = get_routes_wp_waiting_time(vrp_routes_points_wt_clean, WP_WAITING_TIME) 
# add depth info
vrp_routes_points_coord_and_depth_wt_clean = add_depth_info(tbath_op, vrp_routes_points_wt_clean, vrp_routes_points_coord_wt_clean)
# add final displacement
vrp_routes_points_coord_and_depth_wt_clean = add_final_point_displacement(vrp_routes_points_coord_and_depth_wt_clean, START_END_POINT_DISPLACEMENT)
#create the file
create_routes_file_wt('routes_file.txt', vrp_routes_points_coord_and_depth_wt_clean, routes_length_wt, vrp_routes_minimum_depth_wt, routes_waiting_time_clean)  

#################################################################################################################################
###############################################  PLOTS  #########################################################################
#################################################################################################################################


#Operation area with all masks, uncertain points and vrp solution  (final sol)
fig, ax = _plot_base_map(temperr2d_op, 'PC-VRP Solution', cmap_name='viridis')
uncertain_points_for_scatter = [(y, x)  for x, y in uncertain_points]
ax.scatter(*zip(*uncertain_points_for_scatter), s=5, c='grey', marker='o', label = "Total VRP points: "+str(len(uncertain_points))+"\n___________")  #RICORDA LO SCATTER VUOLE PRIMA Y poi X
for i in range(len(vrp_routes_points_wt_clean)):
    single_vrp_route_scatter = [(y, x)  for x, y in vrp_routes_points_wt_clean[i]]
    ax.plot(*zip(*single_vrp_route_scatter), label = "Visited points: "+str(len(vrp_routes_points_wt[i])-2)+"\nWaypoints: "+str(len(vrp_routes_points_wt_clean[i])-2)+"\n___________")
    ax.scatter(*zip(*single_vrp_route_scatter), s=5, c='black', marker='o')
    ax.scatter(single_vrp_route_scatter[0][0], single_vrp_route_scatter[0][1], s=80, c='black', marker='*')    #first point
    ax.scatter(single_vrp_route_scatter[1][0], single_vrp_route_scatter[1][1], s=30, c='purple', marker='o')    #second point
ax.legend(bbox_to_anchor = (1.25, 0.6), loc='upper left')
#save plot
date_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
file_name = "plots/"+str(date_time)+"_wt.png"
fig.savefig(file_name, bbox_inches='tight')
plt.show()
plt.close(fig)



