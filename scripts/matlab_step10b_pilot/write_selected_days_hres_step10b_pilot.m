function hres_table = write_selected_days_hres_step10b_pilot(cfg)
% WRITE_SELECTED_DAYS_HRES_STEP10B_PILOT Build HRes input files for pilot dates.
% This is a non-destructive adaptation of Filipa's write14days.m. It keeps
% the original 14-day window, local crop, and interpolation logic, but uses
% cfg paths/dates and writes only into cfg.output_base.

if nargin < 1
    cfg = step10b_pilot_config();
end

ensure_dir(cfg.cmems_grid_output_dir);
ensure_dir(cfg.hres_output_dir);
ensure_dir(cfg.logs_dir);

required_dates = required_hres_end_dates(cfg);
rows = {};

for k = 1:numel(required_dates)
    end_date = required_dates(k);
    hres_name = ['CMEMSnaza_', datestr(end_date, 'yyyymmdd'), '_HResNew.nc'];
    hres_path = fullfile(cfg.hres_output_dir, hres_name);
    rows(end+1,:) = {datestr(end_date, 'yyyy-mm-dd'), hres_path, cfg.dry_run}; %#ok<AGROW>
    if cfg.dry_run
        fprintf('[DRY-RUN] Would create HRes window ending %s -> %s\n', datestr(end_date), hres_path);
    end
end

hres_table = cell2table(rows, 'VariableNames', {'hres_end_date','hres_path','dry_run'});
writetable(hres_table, fullfile(cfg.logs_dir, 'step10b_hres_generation_plan.csv'));

if cfg.dry_run
    return
end

assert(isfile(cfg.thetao_nc), 'Missing thetao file: %s', cfg.thetao_nc);
assert(isfile(cfg.bathy_reference_hres), 'Missing bathy reference HRes: %s', cfg.bathy_reference_hres);

TIMEALL = ncread(cfg.thetao_nc, 'time');
all_days = datetime(1970,1,1,0,0,0) + seconds(TIMEALL);
lat = ncread(cfg.thetao_nc, 'latitude');
lon = ncread(cfg.thetao_nc, 'longitude');
dept = ncread(cfg.thetao_nc, 'depth');
temp_all = ncread(cfg.thetao_nc, 'thetao');

ref_lat_hres = ncread(cfg.bathy_reference_hres, 'LAT');
ref_lon_hres = ncread(cfg.bathy_reference_hres, 'LON');
ref_bathy_hres = ncread(cfg.bathy_reference_hres, 'BATHY');

for k = 1:numel(required_dates)
    end_date = required_dates(k);
    idx_end = find(dateshift(all_days, 'start', 'day') == dateshift(end_date, 'start', 'day'), 1, 'first');
    if isempty(idx_end)
        error('Date %s not found in thetao_nc time axis.', datestr(end_date, 'yyyy-mm-dd'));
    end
    idx_start = idx_end - cfg.input_days + 1;
    if idx_start < 1
        error('Date %s does not have the required %d-day lookback window.', datestr(end_date, 'yyyy-mm-dd'), cfg.input_days);
    end

    TEMP = squeeze(temp_all(:,:,:,idx_start:idx_end));
    TIME = squeeze(TIMEALL(idx_start:idx_end));

    idxLatMax = find(min(abs(lat-cfg.operation_ur_corner(1))) == abs(lat-cfg.operation_ur_corner(1)), 1) + 4;
    idxLatMin = find(min(abs(lat-cfg.operation_ll_corner(1))) == abs(lat-cfg.operation_ll_corner(1)), 1) - 4;
    idxLonMax = find(min(abs(lon-cfg.operation_ur_corner(2))) == abs(lon-cfg.operation_ur_corner(2)), 1) + 4;
    idxLonMin = find(min(abs(lon-cfg.operation_ll_corner(2))) == abs(lon-cfg.operation_ll_corner(2)), 1) - 4;

    LAT = lat(idxLatMin:idxLatMax);
    LON = lon(idxLonMin:idxLonMax);
    TEMP = TEMP(idxLonMin:idxLonMax, idxLatMin:idxLatMax, :, :);

    inc = cfg.hres_interpolation_factor;
    clear TempHRes
    for dpt = 1:size(TEMP,3)
        for tm = 1:size(TEMP,4)
            [xTq, yTq] = meshgrid(1:size(TEMP,2), 1:size(TEMP,1));
            [xTqnew, yTqnew] = meshgrid(linspace(1, size(TEMP,2), size(TEMP,2)*inc), linspace(1, size(TEMP,1), size(TEMP,1)*inc));
            TempHRes(:,:,dpt,tm) = interp2(xTq, yTq, TEMP(:,:,dpt,tm), xTqnew, yTqnew); %#ok<AGROW>
        end
    end
    LatHRes = interp1((1:size(LAT,1))', LAT, linspace(1, size(LAT,1), size(LAT,1)*inc)');
    LonHRes = interp1((1:size(LON,1))', LON, linspace(1, size(LON,1), size(LON,1)*inc)');

    if numel(LatHRes) ~= numel(ref_lat_hres) || numel(LonHRes) ~= numel(ref_lon_hres)
        error('Computed HRes grid does not match bathy reference grid.');
    end

    out_nc = fullfile(cfg.hres_output_dir, ['CMEMSnaza_', datestr(end_date, 'yyyymmdd'), '_HResNew.nc']);
    if isfile(out_nc)
        delete(out_nc);
    end
    nccreate(out_nc, 'TEMP', 'Dimensions', {'LON',size(TempHRes,1),'LAT',size(TempHRes,2),'DEPT',size(TempHRes,3),'TIME',size(TempHRes,4)});
    nccreate(out_nc, 'LAT', 'Dimensions', {'lat',size(LatHRes,1)});
    nccreate(out_nc, 'LON', 'Dimensions', {'lon',size(LonHRes,1)});
    nccreate(out_nc, 'BATHY', 'Dimensions', {'LON',size(ref_bathy_hres,1),'LAT',size(ref_bathy_hres,2)});
    nccreate(out_nc, 'DEPT', 'Dimensions', {'depth',size(dept,1)});
    nccreate(out_nc, 'TIME', 'Dimensions', {'seconds since 1970-01-01',size(TIME,1)});
    ncwrite(out_nc, 'TEMP', TempHRes);
    ncwrite(out_nc, 'BATHY', ref_bathy_hres);
    ncwrite(out_nc, 'DEPT', dept);
    ncwrite(out_nc, 'LAT', LatHRes);
    ncwrite(out_nc, 'LON', LonHRes);
    ncwrite(out_nc, 'TIME', TIME);
    fprintf('Created %s\n', out_nc);
end
end

function dates = required_hres_end_dates(cfg)
dates = datetime.empty(0,1);
for i = 1:numel(cfg.pilot_dates)
    target = datetime(cfg.pilot_dates{i}, 'InputFormat', 'yyyy-MM-dd');
    dates(end+1,1) = target - days(1); %#ok<AGROW>
    dates(end+1,1) = target + days(1); %#ok<AGROW>
end
dates = unique(dates);
end

function ensure_dir(path_)
if ~exist(path_, 'dir')
    mkdir(path_);
end
end
