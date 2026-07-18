- Dropped 2018 loans: right-censoring bias observed (default rate 
  artificially low since loans hadn't had time to mature/default yet)
- Merged 'Default' and reclassified statuses into Fully Paid/Charged Off
- Excluded joint applications (application_type != 'Individual') for v1
- Capped annual_inc at 99th percentile ($251,000) to handle extreme outliers