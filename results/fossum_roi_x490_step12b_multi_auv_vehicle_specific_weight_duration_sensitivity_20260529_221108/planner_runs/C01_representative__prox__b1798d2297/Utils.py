import numpy as np
import geopy.distance   #pip install geopy
import datetime
import matplotlib.pyplot as plt
from scipy.spatial import distance, Voronoi, voronoi_plot_2d
import decimal
import math 
from Config_file import *


########################################################################################################################################
############################################################### POI FUNCTIONS ##########################################################
########################################################################################################################################


#Find the contour lines
#Input: map, max and minimum range for the contour lines, step
#Output: list of the points, list of points coordinates, list of points level
def get_contour_levels(map, max, min, step):

  max_level = max
  min_level = min
  step_level = step 
  
  dec_num = decimal.Decimal(str(max_level)) #find map res
  res_map = abs(dec_num.as_tuple().exponent)
  
  lev_ = np.arange(min_level + step_level, max_level + step_level, step_level) #find levels value 
  levels_ = []

  for x in lev_: levels_.append(round(x, res_map))  #truncated to the map resolution

  contour_lines = plt.contour(map, levels = levels_, linewidths=1, alpha=1, colors='black') #compute contour lines
 
  contour_points_lat = []
  contour_points_lon = []
  contour_points_level = []

  for i in range(len(contour_lines.allsegs)):
      single_contour = contour_lines.allsegs[i]

      for j in range(len(single_contour)):
          part_of_contour = single_contour[j]
          part_of_contour = [(y, x)  for x, y in part_of_contour]

          for k in range(len(part_of_contour)):
              
              single_point = part_of_contour[k]
  
              contour_points_lat.append(single_point[0])
              contour_points_lon.append(single_point[1])
              contour_points_level.append(i)

  contour_points_lat.reverse()  #from the most uncertain to the lowest
  contour_points_lon.reverse()
  contour_points_level.reverse()

  return contour_points_lat, contour_points_lon, contour_points_level, levels_

#
#Find the point on the contour lines
#
def find_POI_on_contour_levels(D_MIN, contour_points_lat, contour_points_lon, contour_points_level, map_lat, map_lon):

  unc_points = []
  unc_points_coord = []
  unc_points_level = []

  first = True
  
  i = -1
  for x, y, in zip(contour_points_lat, contour_points_lon):

      i = i + 1
      x = round(x)   #assign the nearest integer
      y = round(y)

      point = [x, y]
      point_lat_lon = [map_lat[x], map_lon[y]]
      point_level = contour_points_level[i]
     
      if first:
          unc_points.append(point)
          unc_points_coord.append(point_lat_lon)
          unc_points_level.append(point_level)
          first = False
          continue

      if any((geopy.distance.geodesic(point_lat_lon, point_lat_lon_ok).km < D_MIN for point_lat_lon_ok in unc_points_coord)):
          continue

      unc_points.append(point)
      unc_points_coord.append(point_lat_lon)
      unc_points_level.append(point_level)

  return unc_points, unc_points_coord, unc_points_level

#
# Add additional point inside the contour lines - Voronoi vertex - if uncertanty points > UNC_TRESHOLD
#
def additional_POI_inside_contour_levels(D_MIN, UNC_TRESHOLD, map, contour_level_points_, contour_level_points_coord_, map_lat, map_lon):

  points_copy = contour_level_points_.copy()
  points_coord_copy = contour_level_points_coord_.copy()
 
  vor = Voronoi(points_copy)

  for i in range(len(vor.vertices)):
      x_vertex = round(vor.vertices[i][0])
      y_vertex = round(vor.vertices[i][1])
      vertex = [x_vertex, y_vertex]
      if(is_inside_op_area(map, vertex)):
        unc_value = map[x_vertex, y_vertex]
        if(unc_value >= UNC_TRESHOLD):
            vertex_lat_lon = [map_lat[x_vertex], map_lon[y_vertex]]
            if any((geopy.distance.geodesic(vertex_lat_lon, vertex_lat_lon_ok).km < D_MIN for vertex_lat_lon_ok in points_coord_copy)):
                continue

            points_copy.append(vertex)
            points_coord_copy.append(vertex_lat_lon)
    
  return points_copy, points_coord_copy


########################################################################################################################################
############################################################### VRP FUNCTIONS ##########################################################
########################################################################################################################################

#Get idxs depots points (idx lat- idx lon) on grid map
#Input: Starting points coords, latitude and longitude operational
#Output: list of depots point 
def get_depots(starting_points, ending_points, map_lat_op, map_lon_op):
  
  depots = []

  start_and_end = starting_points + ending_points

  for i in range(len(start_and_end)):
    depot_point = start_and_end[i]

    closest_lat = min(map_lat_op, key=lambda x:abs(x-depot_point[0])) #find closest value in the grid
    closest_lon = min(map_lon_op, key=lambda x:abs(x-depot_point[1]))

    lat_idx = next(x for x, val in enumerate(map_lat_op) if val == closest_lat) #get grid index
    lon_idx = next(x for x, val in enumerate(map_lon_op) if val == closest_lon)  

    depot_point_idx = [lat_idx, lon_idx]

    depots.append(depot_point_idx)

  return depots

#
#Take in input a list of depots and a list of nodes and delete from the list of nodes, the node equal to the depots (if exist)
#
def remove_duplicates(depots, nodes):
  for i in depots[:]:
    if (i in nodes):
        nodes.remove(i)
  return nodes

#Get the price of the points accordly with map value. 
#Input: map of values, points list(depot + other points), number of depots
#Output: an ordered prizes list
def get_nodes_prize(map, points, N_DEPOT):

  prices_list = [0] * N_DEPOT       #note: depot nodes need zero price
  N_level = 1000                    #number of levels to divide the reward bar
  valid_map = map[np.isfinite(map) & (map != -np.inf)]
  if valid_map.size == 0:
    raise RuntimeError("No finite map values available to compute node prizes.")
  max_ = np.max(valid_map)
  min_ = np.min(valid_map)
  range_ = max_ - min_
  if range_ <= 0:
    decimal_number_ = 0
  else:
    decimal_number_ = max(0, math.ceil(-math.log10(range_ / N_level)))  #decimal numbers to have the desired step=range/N_level
  multiplicative_factor = pow(10, decimal_number_)
 
  for i in range(N_DEPOT, len(points)):
    point_val = map[points[i][0], points[i][1]]
    if (np.isfinite(point_val) == False) or (point_val == -np.inf):
      real_price = 0
    else:
      real_price = int(multiplicative_factor * point_val)

    prices_list.append(real_price)  

  #In order to avoid big number in case of low data (temperr) variability:
  if(decimal_number_ > 5 and any(v != 0 for v in prices_list)):
    min_nonzero = min(v for v in prices_list if v != 0)
    max_val = max(prices_list)
    s1, s2 = str(min_nonzero), str(max_val)
    diff_index = next(i for i in range(len(s1)) if s1[i] != s2[i])    #find the first different digit
    offset = int(s1[:diff_index] + '0' * (len(s1) - diff_index))      #pre truncate the numbers to that digit
    normalized = [n - offset if n != 0 else 0 for n in prices_list]
    prices_list[:] = normalized
    print("Weights Normalizzati:", normalized)

  return prices_list

#
#return True if there in obstacle (ob_map = -1) between two points, false otherwise
#
def obstacle_between(ob_map, point_1, point_2):
  ob_between = False
  points_between = connect_points(point_1, point_2) 
  for point in points_between:
    lat = point[0]
    lon = point[1]
    if(ob_map[lat,lon] == -np.inf):
      ob_between = True
      break
  return ob_between


#Get distances between node
# max distance if there is an obstacle between two nodes
# euclidean distance otherwise
def get_nodes_distance(ob_map, nodes):
  dim = (len(nodes), len(nodes))
  distance_matrix = np.zeros(dim)
  for i in range(len(nodes)):
    for j in range(len(nodes)):
      if(obstacle_between(ob_map, nodes[i], nodes[j])):
        distance_matrix[i,j] = 9999999999
        if(i == j): print("Error: Starting or ending point on Mask")
      else:
        distance_matrix[i,j] = distance.euclidean((nodes[i][0], nodes[i][1]), (nodes[j][0], nodes[j][1]))
  return distance_matrix

#
#
#
def from_hour_to_sec(hours):
  seconds = hours * 60 * 60
  return seconds

#
#get vehicles max distance mission durations [km]
#
def get_max_distances(missions_duration):
  path_lengths = []
  for dur in missions_duration: 
    path_lengths.append((dur * SPEED)/1000)  #Single AUV maximum path length in [km]

  print("Maximum path length [km]:")
  print(path_lengths)
  path_lengths_alg = []
  for length in path_lengths:
    length_alg = int((length*1000)/HOPS_GRID_RESOLUTION)  # n_grid_points each path = maximum_path_length in [m] / grid_resolution in [m] = [ad]
    path_lengths_alg.append(length_alg) 

  return path_lengths_alg 

#Create the problem configuration .vrp file 
#Input: mission duration [seconds]
def create_vrp_problem_instance_file(file_name, nodes, distances, prices, auv_number, depot_number, missions_duration):
  
  path_lengths = []
  for dur in missions_duration: 
    path_lengths.append((dur * SPEED)/1000)  #Single AUV maximum path length in [km]

  path_lengths_alg = []
  for length in path_lengths:
    path_lengths_alg.append(int((length*1000)/HOPS_GRID_RESOLUTION) ) # n_grid_points each path = maximum_path_length in [m] / grid_resolution in [m] = [ad]

  file = open(file_name,'w')
  file.write("EDGE_WEIGHT_TYPE: EXPLICIT\n")  #EXPLICIT wp distance are given in an explicit way -  not need the solver to compute them
  file.write("EDGE_WEIGHT_FORMAT: FULL_MATRIX\n")
  file.write("DIMENSION: "+str(len(nodes))+"\n") 
  file.write("VEHICLES: "+str(auv_number)+"\n") 
  file.write("NODE_COORD_SECTION\n")
  for i in range(len(nodes)):   
    file.write(str(i+1)+" "+str(nodes[i][0])+" "+str(nodes[i][1])+"\n")
  file.write("EDGE_WEIGHT_SECTION\n")
  for i in range(len(nodes)): 
    for j in range(len(nodes)):
      file.write(str(round(distances[i][j], 3))+" ")
    file.write("\n")

  file.write("PRIZE_SECTION\n")
  for i in range(len(prices)):   
    file.write(str(i+1)+" "+str(prices[i])+"\n")  
  file.write("DEPOT_SECTION\n")
  for i in range(depot_number):
      file.write(str(i+1)+"\n")

  file.write("EOF")
  file.close()

#Get routes points and coordinates from the vrp best solution and add the depot start and end as first and last node
#Input: Result of the vrp problem (lists of node/client number), list of node/client 2d coord, list of node/client lat lon coord
#Output: list of the points in each routes, list of their coordinates
def get_routes(vrp_best_result, vrp_nodes, vrp_nodes_coord):

  routes_points = []
  routes_points_coord = []
  n_route = len(vrp_best_result)

  for idx, route in enumerate(vrp_best_result, 1):
    single_route = []
    single_route_points = []
    single_route_points_coord = []
    for node in route:
        single_route.append(node)
        single_route_points.append(vrp_nodes[node])
        single_route_points_coord.append(vrp_nodes_coord[node])

    # add start point and final point (first points in the list)   
    single_route_points = [vrp_nodes[idx-1]] + single_route_points + [vrp_nodes[idx + (n_route - 1)]]
    single_route_points_coord = [vrp_nodes_coord[idx-1]] + single_route_points_coord + [vrp_nodes_coord[idx + (n_route - 1)]]
    routes_points.append(single_route_points)
    routes_points_coord.append(single_route_points_coord)

  return routes_points, routes_points_coord

#Return a list: the total amount of time [seconds] (for each route) spent in waiting at every wp
#Input: routes points, wp_waiting time [minutes]
#Output: routes_waiting time [seconds]
def get_routes_wp_waiting_time(vrp_routes_p, wp_waiting_time):
  routes_waiting_time = []
  for i in range(len(vrp_routes_p)):
    single_route_waiting_time = wp_waiting_time * 60 * (len(vrp_routes_p[i])-2)   #[seconds] starting and ending points excluded
    routes_waiting_time.append(single_route_waiting_time)    

  return routes_waiting_time


#Remove the time spent in the wps (routes_waiting_time) from mission duration in order to obtain the effective travel duration
#Input: routes_waiting_time [s], mission_duration [s] 
def get_effective_travel_duration(routes_wt, mission_duration):
  routes_effective_travel_time = []
  #print("Effective travel time for each route [h]:")
  duration_des = []   #save duration desired   
  duration_real = []  #save real duration based of the waiting time
  for i in range(len(mission_duration)):
    dur_des = mission_duration[i]
    dur_real = mission_duration[i] - routes_wt[i]  

    if(dur_des in duration_des): #give same real duration for vechiles with same desired duration
      idx = duration_des.index(dur_des)
      single_effective_travel_time = duration_real[idx]
    else:
      duration_des.append(dur_des)
      duration_real.append(dur_real)
      single_effective_travel_time = dur_real

    routes_effective_travel_time.append(single_effective_travel_time) 

  return routes_effective_travel_time 


#Find the grid points existing between two grid points
#input: 2 points grid coordinates
#output: list with all the points between
def connect_points(first_point, second_point):
  two_points = np.array([first_point, second_point])
  d0, d1 = np.abs(np.diff(two_points, axis=0))[0]
  if d0 > d1: 
    intermediate_points = np.c_[np.linspace(two_points[0, 0], two_points[1, 0], (d0+1)*2, dtype=np.int32),
                                np.round(np.linspace(two_points[0, 1], two_points[1, 1], (d0+1)*2))
                                .astype(np.int32)]
    intermediate_points = intermediate_points.tolist()

    return intermediate_points
  else:
    intermediate_points = np.c_[np.round(np.linspace(two_points[0, 0], two_points[1, 0], (d1+1)*2))
                                .astype(np.int32),
                                np.linspace(two_points[0, 1], two_points[1, 1], (d1+1)*2, dtype=np.int32)]
    intermediate_points = intermediate_points.tolist()
    return intermediate_points

#Find all the grid points intersecated by the route path
#input: routes
#output: list of the routes grid points
def get_all_routes_grid_points(routes):

  all_routes = []
  for j in range(len(routes)):
    
    single_route = []
    first_segment = True
    
    for i in range(len(routes[j])-1):
      segment = connect_points(routes[j][i], routes[j][i+1])
      if (first_segment == False): segment.pop(0) #delete first element of segment to avoid repetition (skip it just in the first segment to save the depot)
      first_segment = False
      for point in segment: 
        single_route.append(point)
    
    all_routes.append(single_route)
  
  return all_routes

#Find the price of a route
#Input: map of price, the route
#Output: price of the route
def get_single_route_prize(price_map, route):
  
  price = 0.0
  for j in range(len(route)):
    if(price_map[route[j][0], route[j][1]] != -np.inf):
      price = price + price_map[route[j][0], route[j][1]]
  return price

#Find the sum of routes prizes
#Input: map of price, the routes
#Output: sum of price routes prizes
def get_routes_prize(price_map, routes):
  
  total_price = 0.0
  for i in range(len(routes)):
    single_price = get_single_route_prize(price_map, routes[i])
    total_price = total_price + single_price
  
  return total_price

# check if a point is inside the operational area
#Input: operational area map, point
#Output: True if is inside, False otherwise
def is_inside_op_area(op_map, point):
  is_inside = False
  dimension_op = op_map.shape
  if (point[0] >= 0 and point[1] >= 0 and point[0] < dimension_op[0] and point[1] < dimension_op[1]):
    point_value = op_map[round(point[0]), round(point[1])]
    if(point_value != -np.inf):
      is_inside = True 
  return is_inside

#
#get distance route in [km] 
#
def get_routes_length(routes_points_coord):
  lengths = []
  for single_route in range(len(routes_points_coord)):
      
      route_node_coord = routes_points_coord[single_route]

      current_distance = 0.0

      for i in range(len(route_node_coord)-1):
          current_distance = current_distance + geopy.distance.geodesic(route_node_coord[i], route_node_coord[i+1]).km
      
      lengths.append(current_distance)

  return lengths

#
#Get the minimum depth value for each route (every grid points are checked) 
#
def get_routes_minimum_depth(depth_map_op, routes_total_points):
  routes_minimum_depth = []
  for single_route in routes_total_points:
      route_depth_values = []
      
      for i in range(len(single_route)):
        point_depth = - depth_map_op[single_route[i][0], single_route[i][1]] #if Fresnel hops different sign, change it
        route_depth_values.append(point_depth)
      
      min_depth = min(route_depth_values)  
      routes_minimum_depth.append(min_depth)  

  return routes_minimum_depth

#Function that change the final point of the route with one that has a displacement [m]
# if the final point == starting point and dist(final_point, starting point) > displacement value
# along the line connecting the last point and the second to last point
def add_final_point_displacement(routes_coord_and_depth, displacement):
  routes_coord_and_depth_disp = []
  
  for single_route in routes_coord_and_depth:

    first_point_with_depth = single_route[0]
    last_coord_with_depth = single_route[len(single_route)-1]
    second_last_coord_with_depth = single_route[len(single_route)-2]

    last_coord_depth = last_coord_with_depth[2]
    first_coord = [first_point_with_depth[0], first_point_with_depth[1]]
    last_coord = [last_coord_with_depth[0], last_coord_with_depth[1]]
    second_last_coord = [second_last_coord_with_depth[0], second_last_coord_with_depth[1]]

    if(geopy.distance.geodesic(last_coord, first_coord).m != 0):  #start point != end point > No displacement needed
      routes_coord_and_depth_disp.append(single_route)

    elif(geopy.distance.geodesic(last_coord, second_last_coord).m <= displacement): #second to last too close to last > use second to last as final point (no space for intermedium point)
      changed_route = single_route[:-1]
      routes_coord_and_depth_disp.append(changed_route)

    else: #start point == last point > displacement needed
      changed_route = single_route
      dist_m = geopy.distance.geodesic(last_coord, second_last_coord).m

      lat_final = (((dist_m - displacement) * last_coord[0]) + (displacement * second_last_coord[0]))/(dist_m)
      lon_final = (((dist_m - displacement) * last_coord[1]) + (displacement * second_last_coord[1]))/(dist_m)

      final_ = [lat_final, lon_final, last_coord_depth]

      changed_route = single_route[:-1] + [final_]

      routes_coord_and_depth_disp.append(changed_route)

  return routes_coord_and_depth_disp

#
#Create the Routes file (just debug) 
#
def create_routes_file(file_name, routes, lenghts, min_depths):

  file = open(file_name,'w')

  date_time = datetime.datetime.utcnow()
 
  file.write("#FRESNEL OPTIMAL PLANNING - GENERATION DATA - ESTIMATION \n")
  file.write("#TIMESTAMP: "+str(date_time)+" [UTC]\n")
  file.write("#AUV_NUMBER: "+str(AUV_NUMBER)+"\n")
  file.write("#SPEED: "+str(SPEED)+"  [m/s]\n")
  file.write("#ROUTES WAYPOINTS:  (lat, lon, depth)\n")
  for i in range(len(routes)): 
    duration_s = ((lenghts[i]*1000)/SPEED)  #[s] 
    duration_m = duration_s/60              #[m] 
    duration_h = math.trunc(duration_m/60)  #[h]  
    left_m = math.trunc(duration_m - (duration_h * 60)) 
  
    file.write("#Length_2D: "+str(round(lenghts[i], 3))+" [km]"+" Travel_duration: "+str(duration_h)+" [h] "+str(left_m)+" [m]"+" Minimum_depth: "+str(min_depths[i])+" [m]\n ")
    single_route = routes[i]
    for j in range(len(single_route)):
       wp = single_route[j]    
       wp_ = ", ".join(map(str, wp))     
       if (j == len(single_route)): file.write("\n")
       else: file.write(wp_+"; ")
    file.write("\n")
 

  file.close()


#Create the Routes file for NEPTUS 
def create_routes_file_wt(file_name, routes, lenghts, min_depths, waiting_times):

  file = open(file_name,'w')

  date_time = datetime.datetime.utcnow()
 
  file.write("#FRESNEL OPTIMAL PLANNING - GENERATION DATA \n")
  file.write("#TIMESTAMP: "+str(date_time)+" [UTC]\n")
  file.write("#AUV_NUMBER: "+str(AUV_NUMBER)+"\n")
  file.write("#SPEED: "+str(SPEED)+"  [m/s]\n")
  file.write("#WP_WAITING_TIME: "+str(WP_WAITING_TIME)+"  [m]\n")
  file.write("#ROUTES SPECS:  waypoints(lat, lon, depth) - length_2d(same depth length) - travel_duration(no wp waiting time) - mission_duration(travel_duration + wp waiting time) -  minimum_depth(min depth along the route)\n")
  for i in range(len(routes)): 
    t_duration_s = ((lenghts[i]*1000)/SPEED)    #[s] Travel time duration
    t_duration_m = t_duration_s/60              #[m] 
    t_duration_h = math.trunc(t_duration_m/60)  #[h]  
    t_left_m = math.trunc(t_duration_m - (t_duration_h * 60)) 

    m_duration_s = t_duration_s + waiting_times[i]     #[s] Mission time duration = travel time + waiting time
    m_duration_m = m_duration_s/60                     #[m] 
    m_duration_h = math.trunc(m_duration_m/60)         #[h]  
    m_left_m = math.trunc(m_duration_m - (m_duration_h * 60)) 
  
    file.write("#length_2D: "+str(round(lenghts[i], 3))+" [km]"+" travel_duration: "+str(t_duration_h)+" [h] "+str(t_left_m)+" [m]"+" mission_duration: "+str(m_duration_h)+" [h] "+str(m_left_m)+" [m]"+" minimum_depth: "+str(min_depths[i])+" [m]\n ")
    single_route = routes[i]
    for j in range(len(single_route)):
       wp = single_route[j]    
       wp_ = ", ".join(map(str, wp))     
       if (j == len(single_route)): file.write("\n")
       else: file.write(wp_+"; ")
    file.write("\n")
 

  file.close()

# Add depth information to the waypoints
#Input: operational depth map, list of waypoints points in the grid, list of waypoints coords
#Output: list of wayponts and depth info
def add_depth_info(depth_map_op, routes_points, routes_coords):
  routes_coords_and_depth = []

  for i in range(len(routes_points)):
    single_route_points = routes_points[i]
    single_route_coords = routes_coords[i]
    single_route_coords_and_depth = []

    for j in range(len(single_route_points)):
      wp_depth = - depth_map_op[single_route_points[j][0], single_route_points[j][1]] #if Fresnel hops different sign, change it
      wp_coords_and_depth = [single_route_coords[j][0], single_route_coords[j][1], wp_depth]
      single_route_coords_and_depth.append(wp_coords_and_depth)

    routes_coords_and_depth.append(single_route_coords_and_depth)

  return routes_coords_and_depth


#Function that return True if the point is redundant,false otherwise
#redundant = wp in straight line 
#Input: route (list), point idx in the route list
#Output: bool
def is_wp_redundant(route, point_idx):
  if(point_idx == 0 or point_idx == len(route)-1): return False 
  else:
    lat_point = route[point_idx][0]     #Selected point
    lon_point = route[point_idx][1]

    lat_prev = route[point_idx - 1][0]  #Previous point
    lon_prev = route[point_idx - 1][1]

    lat_next = route[point_idx + 1][0]  #Next point
    lon_next = route[point_idx + 1][1]

    segment = connect_points(route[point_idx - 1], route[point_idx + 1])  #compute segment between previous and next wp
    #check if the selected point is in the segment
    if( route[point_idx] in segment): return True
    else: return False

#Function that return True if the wp is necessary for safe contraints
#i.e: if the wp is necessary for avoid the mask
#input: obstacles map of value, route with all wp, route with a selection of wp, the idx of the route 1
#can we delete this wp and have a route_new safe? this function will tell you
def is_wp_safety_necessary(ob_map, route_original, route_new, wp_idx):
  if(wp_idx == 0 or wp_idx == len(route_original)-1): return True 
  else:
    last_point_new_route = route_new[len(route_new)-1]
    next_point_original_route = route_original[wp_idx + 1]
    if(obstacle_between(ob_map, last_point_new_route, next_point_original_route)): return True
    else: return False


#Function that clean the route deleting the unnecessary wp 
#redundant wp is a wp in straight line(redundant wps in straight line)
def delete_redundant_wp(ob_map, routes_points, routes_coords):
  routes_less_points = []
  routes_less_coords = []
  for i in range(len(routes_points)):
    single_route_points = routes_points[i]
    single_route_coords = routes_coords[i]
    single_route_less_points = []
    single_route_less_coords = []

    for j in range(len(single_route_points)):
      
      if(is_wp_redundant(single_route_points, j) == False or (is_wp_redundant(single_route_points, j) == True and is_wp_safety_necessary(ob_map, single_route_points, single_route_less_points, j) == True)): 
        single_route_less_points.append(single_route_points[j])
        single_route_less_coords.append(single_route_coords[j])

    routes_less_points.append(single_route_less_points)
    routes_less_coords.append(single_route_less_coords)
  return routes_less_points, routes_less_coords



