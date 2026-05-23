function sim_table = run_selected_days_simulations_step10b_pilot(cfg)
% RUN_SELECTED_DAYS_SIMULATIONS_STEP10B_PILOT Run DSS pilot simulations.
% Non-destructive adaptation of Filipa's runSimulations.m. Dry-run is the
% default and only prints expected work. Set cfg.dry_run=false after checking
% paths and HRes inputs.

if nargin < 1
    cfg = step10b_pilot_config();
end

addpath(genpath(cfg.filipa_code_root));
ensure_dir(cfg.sim_output_root);
ensure_dir(cfg.logs_dir);

rows = {};
for day_idx = 1:numel(cfg.pilot_dates)
    targetDate = datetime(cfg.pilot_dates{day_idx}, 'InputFormat', 'yyyy-MM-dd');
    predDate = targetDate - days(1);
    projectPath = fullfile(cfg.sim_output_root, ['Daily_dpt_', datestr(predDate, 'yyyymmdd')]);
    hresFile = fullfile(cfg.hres_output_dir, ['CMEMSnaza_', datestr(predDate, 'yyyymmdd'), '_HResNew.nc']);
    expectedFirst = fullfile(projectPath, [datestr(targetDate, 'dd-mm-yyyy'), '_predModel_1.nc']);
    rows(end+1,:) = {datestr(targetDate,'yyyy-mm-dd'), datestr(predDate,'yyyy-mm-dd'), hresFile, expectedFirst, cfg.dry_run}; %#ok<AGROW>
    if cfg.dry_run
        fprintf('[DRY-RUN] Would simulate target %s using HRes %s\n', datestr(targetDate), hresFile);
    end
end

sim_table = cell2table(rows, 'VariableNames', {'target_date','pred_date','hres_file','expected_predmodel_1','dry_run'});
writetable(sim_table, fullfile(cfg.logs_dir, 'step10b_simulation_plan.csv'));
if cfg.dry_run
    return
end

assert(isfile(cfg.dss_exe), 'Missing DSS executable: %s', cfg.dss_exe);

for day_idx = 1:numel(cfg.pilot_dates)
    targetDate = datetime(cfg.pilot_dates{day_idx}, 'InputFormat', 'yyyy-MM-dd');
    predDate = targetDate - days(1);
    projectPath = fullfile(cfg.sim_output_root, ['Daily_dpt_', datestr(predDate, 'yyyymmdd')]);
    ensure_dir(projectPath);
    imagesPath = fullfile(projectPath, 'Images');
    ensure_dir(imagesPath);

    fileReal = fullfile(cfg.hres_output_dir, ['CMEMSnaza_', datestr(predDate, 'yyyymmdd'), '_HResNew.nc']);
    assert(isfile(fileReal), 'Missing HRes input: %s', fileReal);

    temp = ncread(fileReal, 'TEMP');
    lat = ncread(fileReal, 'LAT');
    lon = ncread(fileReal, 'LON');
    bath = ncread(fileReal, 'BATHY');
    depth = ncread(fileReal, 'DEPT');

    for dpt = cfg.depth_indices
        priorFolderName = ['Priori_Nazare_', datestr(targetDate, 'dd-mm-yyyy'), '_', num2str(dpt)];
        pUTM = projcrs(32629);
        variogram = cfg.variogram(dpt,:);
        LAT = lat;
        LON = lon;
        TEMP = squeeze(temp(:,:,dpt,:));
        BATH = bath;
        TEMP(TEMP == 0) = NaN;

        nx = size(TEMP,1);
        ny = size(TEMP,2);
        inputDays = cfg.input_days;
        outputDays = cfg.output_days;
        nz = inputDays + outputDays;
        ox = 1; oy = 1; oz = 1;
        dx = 1; dy = 1; dz = 1;
        rangeX = variogram(:,1);
        rangeY = variogram(:,2);
        rangeZ = variogram(:,3);

        outputPath = fullfile(projectPath, priorFolderName);
        inputPath = fullfile(outputPath, 'input_all');
        ensure_dir(outputPath);
        ensure_dir(inputPath);
        copyfile(cfg.dss_exe, fullfile(inputPath, 'DSS.C.64.exe'));

        hardata = ones(1,4);
        dept_counter = 1;
        for y = oy:ny
            for x = ox:nx
                for z = oz:inputDays
                    if ~isnan(TEMP(x,y,z))
                        hardata(dept_counter,:) = [x, y, z, TEMP(x,y,z)];
                        dept_counter = dept_counter + 1;
                    end
                end
            end
        end
        seconddata = [hardata(:,1)+10000, hardata(:,2)+10000, hardata(:,3), hardata(:,4)];

        mask = zeros(nx*ny*nz,4);
        mask_counter = 1;
        for z = oz:nz
            for y = oy:ny
                for x = ox:nx
                    if isnan(TEMP(x,y,1))
                        mask(mask_counter,:) = [x, y, z, -1];
                    else
                        mask(mask_counter,:) = [x, y, z, 0];
                    end
                    mask_counter = mask_counter + 1;
                end
            end
        end
        grid2gslib(mask(:,4), fullfile(inputPath, 'mask.out'));
        grid2gslib(BATH, fullfile(outputPath, 'Bath.gslib'));

        write_harddata(fullfile(inputPath, 'temp.gslib'), hardata);
        write_harddata(fullfile(inputPath, 'auxi.gslib'), seconddata);

        writealldata_naza([inputPath, filesep], 'alldata', [outputPath, filesep], dpt, TEMP, ox, oy, oz, nx, ny, inputDays, outputDays, pUTM, LAT, LON, predDate, cfg.hres_output_dir, dpt);

        nbrSim = cfg.nbr_sim;
        covTab = [200 200 200];
        krig_RANGE = [rangeX*2 rangeY*2 rangeZ*2];
        krig_ANG = [0 0 0; 0 0 0; 0 0 0];
        var_temp_ANG = [0 0 0; 0 0 0; 0 0 0];
        var_temp_RANGE = [rangeX rangeY rangeZ 0.9; rangeX rangeY rangeZ 0.9];
        varType = [1; 1; 1];
        varNugget = [0.1; 0.1; 0.1];
        zonesFileName = fullfile(inputPath, 'mask.out');
        bounds = repmat([min(hardata(:,4)) max(hardata(:,4))], 2, 1);

        parFileDSS('GEOEAS', 0, 0, 0, [inputPath, filesep], [[inputPath, filesep, 'temp.gslib']; [inputPath, filesep, 'auxi.gslib']], ...
            nbrSim, fullfile(outputPath, 'sim'), 0, 'no file', ['no file'; 'no file'], bounds, ...
            [nx, ox, dx], [ny, oy, dy], [nz, oz, dz], 'no file', 0, 'no file', krig_ANG, krig_RANGE, ...
            var_temp_ANG, var_temp_RANGE, varType, varNugget, zonesFileName, 2, 10, 0, 'no file', 0, ...
            'no file', 0, covTab);

        readoutput_AUV(0, nbrSim, nx, ny, nz, [inputPath, filesep], [outputPath, filesep], inputDays);
        copyfile(fullfile(inputPath, 'auxi.gslib'), fullfile(outputPath, 'auxi.gslib'));
        copyfile(fullfile(inputPath, 'temp.gslib'), fullfile(outputPath, 'temp.gslib'));
        copyfile(fullfile(inputPath, 'mask.out'), fullfile(outputPath, 'mask.out'));
        copyfile(fullfile(inputPath, 'alldatacoor.gslib'), fullfile(outputPath, 'alldatacoor.gslib'));

        ncfilename = [datestr(targetDate, 'dd-mm-yyyy'), '_predModel_', num2str(dpt), '.nc'];
        copyfile(fileReal, fullfile(outputPath, ncfilename));
        delete(fullfile(inputPath, 'auxi.gslib'));
        delete(fullfile(inputPath, 'temp.gslib'));
        delete(fullfile(inputPath, 'mask.out'));

        giveCoordinateInformation_naza(0, 1, outputDays, imagesPath, [inputPath, filesep], [outputPath, filesep], inputDays, nx, ny, ncfilename);
        copyfile(fullfile(outputPath, ncfilename), fullfile(projectPath, ncfilename));
        save(fullfile(outputPath, 'finalworkspace.mat'));
        fprintf('Created %s\n', fullfile(projectPath, ncfilename));
    end
end
end

function ensure_dir(path_)
if ~exist(path_, 'dir')
    mkdir(path_);
end
end

function write_harddata(path_, data)
fid = fopen(path_, 'w');
fprintf(fid, '%s\n', 'seasurftemp');
fprintf(fid, '%s\n', '4');
fprintf(fid, '%s\n', 'x');
fprintf(fid, '%s\n', 'y');
fprintf(fid, '%s\n', 'z');
fprintf(fid, '%s\n', 'temp');
for f = 1:size(data,1)
    fprintf(fid, '%f\t', data(f,:));
    fprintf(fid, '\n');
end
fclose(fid);
end
