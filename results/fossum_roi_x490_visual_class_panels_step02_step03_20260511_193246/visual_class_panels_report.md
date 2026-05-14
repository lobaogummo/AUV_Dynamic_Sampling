# Visual class panels report

## Inputs
- Step00: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step00_dataset_20260509_232915`
- Step02: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step02_patch_sensitivity_20260510_112924`
- Step03: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step03_dictionary_sensitivity_20260510_231620`
- Seed used: 11

## Method
The selected configurations were recomputed only to obtain complete assignments for all 370 days. The legacy faithful-initial logic was preserved: valid-mask channel, full sparse feature vector, MiniBatchDictionaryLearning, sparse coding, and Ward clustering with n_classes=4. Rankings were not recalculated or replaced.

## Patch panels
- patch_40x24: class sizes [101, 113, 108, 48], mean ICV 1706.822, panel `results\fossum_roi_x490_visual_class_panels_step02_step03_20260511_193246\patch_visual_panels\patch_40x24_seed11_all_members_by_class.png`
- patch_48x32: class sizes [117, 107, 97, 49], mean ICV 1723.554, panel `results\fossum_roi_x490_visual_class_panels_step02_step03_20260511_193246\patch_visual_panels\patch_48x32_seed11_all_members_by_class.png`
- patch_32x20: class sizes [151, 93, 56, 70], mean ICV 1590.730, panel `results\fossum_roi_x490_visual_class_panels_step02_step03_20260511_193246\patch_visual_panels\patch_32x20_seed11_all_members_by_class.png`

## Dictionary panels
- dict2_patch40x24: class sizes [150, 107, 62, 51], mean ICV 1478.119, panel `results\fossum_roi_x490_visual_class_panels_step02_step03_20260511_193246\dictionary_visual_panels\dict2_patch40x24_seed11_all_members_by_class.png`
- dict4_patch40x24: class sizes [101, 113, 108, 48], mean ICV 1706.822, panel `results\fossum_roi_x490_visual_class_panels_step02_step03_20260511_193246\dictionary_visual_panels\dict4_patch40x24_seed11_all_members_by_class.png`
- dict3_patch40x24: class sizes [163, 111, 48, 48], mean ICV 1832.408, panel `results\fossum_roi_x490_visual_class_panels_step02_step03_20260511_193246\dictionary_visual_panels\dict3_patch40x24_seed11_all_members_by_class.png`

## Comparison figures
- `results\fossum_roi_x490_visual_class_panels_step02_step03_20260511_193246\comparison_panels\patch_visual_comparison_top_configs.png`
- `results\fossum_roi_x490_visual_class_panels_step02_step03_20260511_193246\comparison_panels\dictionary_visual_comparison_top_configs.png`
- `results\fossum_roi_x490_visual_class_panels_step02_step03_20260511_193246\comparison_panels\visual_ranking_summary_panel.png`

## Notes
- Missing equivalent full-member outputs in previous runs: none after generation
- Specific configurations recomputed: ['patch_40x24_seed11', 'patch_48x32_seed11', 'patch_32x20_seed11', 'dict2_patch40x24_seed11', 'dict4_patch40x24_seed11', 'dict3_patch40x24_seed11']
- No Step00, Step02, or Step03 files were modified.
