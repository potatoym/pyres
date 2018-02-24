# -*- coding: utf-8 -*-
"""
Created on Thu May 25 08:06:54 2017

Example of a pyres implementation of "Surface electorde array 7" from the 
R2_v3.1_readme.pdf

@author: kbefus
"""
from __future__ import print_function
import os
from shutil import copyfile
import numpy as np

from pyres import mesh_tools, mesh_utils
from pyres import r2_tools
from pyres import pyres_utils, plot_utils

#%%
# Define directory where example scripts are located
ex_dir = r'C:\ER' 
main_work_dir = os.path.join(ex_dir,r'R2_examples\Surface_7\dpdp\Forward_{}')
inv_work_dir = os.path.join(ex_dir,r'R2_examples\Surface_7\dpdp\Inverse_difference')
start_inv_work_dir = os.path.join(inv_work_dir,'Start_resis')

# Define directory with R2
exe_dir = os.path.join(ex_dir,r'R2\Distribition_3.1\Progs')

# ----------------- Define target -----------------
main_res = 100 # ohm m
target_res = 10 # ohm m

# Assign regions for each time step
target_xypos_t0 = [[14,1],[16,1],
                [16,4],[14,4]] # do not want a closed polygon
                   
target_xypos_t1 = [[16,1],[18,1],
                [18,6],[16,6]] # do not want a closed polygon

target_regions = [None,target_xypos_t0,target_xypos_t1]


# -------- Create mesh -------------
n_electrodes = 25.
e_spacing = 2. # meters is unit of distance for this example
ndivx,ndivy = 8.,8. # mesh divisions between electrodes
dx_foreground = e_spacing/ndivx # 0.25 m
dy_foreground = e_spacing/ndivy # 0.25 m  
xbuff,ybuff = 2.,10. # meters to extend foreground beyond electrode x,y locations
dx_background = [0.5,1., 2., 5., 10., 20., 50., 100.]
dy_background = [0.5,1., 2., 5., 10., 20., 50., 100.]

# Define mesh nodes
electrode_x = e_spacing*np.arange(n_electrodes) # first electrode at x=0, last electrode at x=48
xx_mesh = np.arange(electrode_x[0]-xbuff,electrode_x[-1]+xbuff+dx_foreground,dx_foreground)
xx_mesh = np.unique(np.hstack([(xx_mesh[0]-np.cumsum(dx_background))[::-1],
                               xx_mesh,
                               xx_mesh[-1]+np.cumsum(dx_background),
                               electrode_x]))

yy_mesh = np.arange(0,ybuff+dy_foreground,dy_foreground)
yy_mesh = np.hstack([yy_mesh,yy_mesh[-1]+np.cumsum(dy_background)])

# Define mesh creation input
node_dict = {'xx':xx_mesh,'yy':yy_mesh,'topog':None}

# Define electrode rows and columns
e_rows = np.ones_like(electrode_x) # all in top row
e_cols = np.array([(xx_mesh==ix).nonzero()[0][0] for ix in electrode_x])+1 # find columns of electrode nodes
electrode_array = np.column_stack([np.arange(e_cols.shape[0])+1,e_cols,e_rows]).astype(int)

mesh_type = 4 # 4= simple quadrilateral element mesh
output_xy = [[electrode_x[0],0.],[electrode_x[-1],0.],
             [electrode_x[-1],-8.],[electrode_x[0],-8.],
             [electrode_x[0],0.]] # closed polygon outlining main domain
      
# Make synthetic electrode combinations for forward model
synth_dict = {'n_electrodes':n_electrodes,'array_type':'dpdp',
              'max_dipole':1,'max_separation':7}
protocol_data = pyres_utils.make_synthetic_survey(**synth_dict)
protocol_data = protocol_data[:,np.array([0,3,4,1,2])] # reorganize to match example
    
out_fwd_dirs = []
for itime,target_xypos in enumerate(target_regions):

    region_dict = {'mesh_xy':[xx_mesh,yy_mesh],'target_xypos':target_xypos,
                   'target_res':target_res,'background_res':main_res}
    region_elems = mesh_utils.quad_mesh_region(**region_dict)
    
    
    # ----------------- Setup R2 inputs ----------------
    job_type = 0 # 0=forward, 1=inverse model
    if itime==0:
        survey_name = 'Surface_7_dpdp_Forward_homog'    
        work_dir = main_work_dir.format('homog')
        out_temp=[]

    else:
        survey_name = 'Surface_7_dpdp_t{}'.format(itime)
        work_dir = main_work_dir.format(''.join(['t',str(itime)]))
        out_temp=[]#output_xy
        
    if not os.path.isdir(work_dir):
        os.makedirs(work_dir)
    
    out_fwd_dirs.append(work_dir)    
    
    r2_dict = {'survey_name':survey_name,
               'survey_dir': work_dir, 'job_type':job_type,
               'exe_dir':exe_dir,
               'exe_name':'R2.exe'}
    iR2 = r2_tools.R2(**r2_dict)
    

    r2_in_dict = {'electrode_array':electrode_array,
                  'output_domain':out_temp,'mesh_type':mesh_type,
                  'reg_elems':region_elems,
                  'res_matrix':0,
                  'singular_type':0,'node_dict':node_dict}
    

    protocol_dict = {'meas_data':protocol_data}
    
    # ------------- Run R2 forward model ----------------
    run_r2_dict = {'protocol_dict':protocol_dict, 'r2_in_dict':r2_in_dict,
                    'run_bool':True}
    
    iR2.run_all(**run_r2_dict)


#%% Invert t0 data for reference model

if not os.path.isdir(start_inv_work_dir):
    os.makedirs(start_inv_work_dir)

inv_r2_dict = {}
inv_r2_dict.update(r2_dict) # take inputs from forward model
inv_r2_dict.update({'job_type':1,
                    'survey_dir': start_inv_work_dir,
                    'survey_name':'Surface_7_dpdp_Forward_homog'}) # run inverse model and save to new directory

iR2_inv = r2_tools.R2(**inv_r2_dict)

# Assign inversion options when different from r2_tools.inv_defaults
inv_options = {'a_wgt':1e-4,'b_wgt':2e-4,
               'inverse_type':1,'patch_size_xy':[4,4],
               'rho_min':-1e3,'rho_max':1e3,'reg_mode':0,'data_type':1}

inv_r2_in_dict = {}
inv_r2_in_dict.update(r2_in_dict)
inv_r2_in_dict.update({'reg_elems':[[1,int((xx_mesh.shape[0]-1)*(yy_mesh.shape[0]-1)),main_res*10.]],
                       'res_matrix':1,
                       'inv_dict':inv_options,
                       'output_domain':[]})

# Load forward model data
meas_fwd_data = pyres_utils.load_fwd_output(work_dir=out_fwd_dirs[0])

inv_protocol_dict = {'meas_data':meas_fwd_data}
run_inv_r2_dict = {'protocol_dict':inv_protocol_dict, 'r2_in_dict':inv_r2_in_dict,
                   'run_bool':True}

iR2_inv.run_all(**run_inv_r2_dict)


#%% Run difference inversion

if not os.path.isdir(inv_work_dir):
    os.makedirs(inv_work_dir)

# Copy output from reference inversion to inv_work_dir
ref_inv_output = os.path.join(start_inv_work_dir,'f001_res.dat')
ref_start_model = os.path.join(inv_work_dir,'Start_resis.dat')

copyfile(ref_inv_output, ref_start_model)

inv_r2_dict = {}
inv_r2_dict.update(r2_dict) # take inputs from forward model
inv_r2_dict.update({'job_type':1,
                    'survey_dir': inv_work_dir,
                    }) # run inverse model and save to new directory

iR2_inv = r2_tools.R2(**inv_r2_dict)

# Assign inversion options when different from r2_tools.inv_defaults
inv_options2 = {'a_wgt':1e-3,'b_wgt':1e-2,
               'inverse_type':1,'patch_size_xy':[4,4],
               'rho_min':-1e3,'rho_max':1e3,'reg_mode':2,'data_type':0}

inv_r2_in_dict2 = {}
inv_r2_in_dict2.update(r2_in_dict)
inv_r2_in_dict2.update({'reg_elems':None,
                        'output_domain':output_xy,
                       'startingRfile':'Start_resis.dat',
                       'res_matrix':1,
                       'inv_dict':inv_options2})

# Load forward model data
meas_fwd_data_t0 = pyres_utils.load_fwd_output(work_dir=out_fwd_dirs[1])
meas_fwd_data_t1 = pyres_utils.load_fwd_output(work_dir=out_fwd_dirs[2])

# Need to append column of t1 measurements
meas_fwd_data = np.column_stack([meas_fwd_data_t0,meas_fwd_data_t1[:,5]])

inv_protocol_dict2 = {'meas_data':meas_fwd_data}
run_inv_r2_dict2 = {'protocol_dict':inv_protocol_dict2, 'r2_in_dict':inv_r2_in_dict2,
                   'run_bool':True}

iR2_inv.run_all(**run_inv_r2_dict2)



#%%
# Plot % difference of inverse model results
plot_dict = {'fname':os.path.join(inv_work_dir,'f001_diffres.dat'),
             'inv_col':2,
             'plt_opts':{'vmin':-1e2,'vmax':1e2,'aspect':2},
             'invert_y':False,'nxny':[5e2,1e2],
             'cmap':'rainbow','keep_log':False}
fig,ax,_  = plot_utils.plot_res(**plot_dict)

# Plot results of difference inversion for time 2
plot_dict = {'work_dir':inv_work_dir,
             'plt_opts':{'vmin':10**1.3,'vmax':10.**2,'aspect':2},
             'invert_y':False,'nxny':[5e2,1e2],
             'cmap':'rainbow','keep_log':True}
fig,ax,_ = plot_utils.plot_res(**plot_dict)