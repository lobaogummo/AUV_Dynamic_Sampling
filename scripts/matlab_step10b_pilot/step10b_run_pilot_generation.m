function step10b_run_pilot_generation()
% STEP10B_RUN_PILOT_GENERATION Controller for safe MATLAB pilot generation.
cfg = step10b_pilot_config();
if ~exist(cfg.output_base, 'dir'); mkdir(cfg.output_base); end
if ~exist(cfg.logs_dir, 'dir'); mkdir(cfg.logs_dir); end
diary(fullfile(cfg.logs_dir, 'step10b_matlab_pilot_run.log'));
cleanup = onCleanup(@() diary('off'));

fprintf('Step10B MATLAB pilot generation\n');
fprintf('dry_run = %d\n', cfg.dry_run);
validate_step10b_config(cfg);
hres_table = write_selected_days_hres_step10b_pilot(cfg);
sim_table = run_selected_days_simulations_step10b_pilot(cfg);
save(fullfile(cfg.logs_dir, 'step10b_matlab_run_workspace.mat'), 'cfg', 'hres_table', 'sim_table');
fprintf('Step10B MATLAB pilot generation finished.\n');
end

function validate_step10b_config(cfg)
assert(isfolder(cfg.repo_root), 'Missing repo_root: %s', cfg.repo_root);
assert(isfolder(cfg.filipa_root), 'Missing filipa_root: %s', cfg.filipa_root);
assert(isfile(cfg.thetao_nc), 'Missing thetao_nc: %s', cfg.thetao_nc);
assert(isfile(cfg.dss_exe), 'Missing dss_exe: %s', cfg.dss_exe);
assert(isfile(cfg.bathy_reference_hres), 'Missing bathy_reference_hres: %s', cfg.bathy_reference_hres);
assert(numel(cfg.pilot_dates) == numel(cfg.pilot_classes), 'pilot_dates/classes size mismatch');
end
