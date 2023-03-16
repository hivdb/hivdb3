INSERT INTO invitro_selected_mutations
  SELECT 
    iv.ref_name,
    iv.isolate_name,
    gene,
    position,
    amino_acid,
    EXISTS (
      SELECT 1 FROM mutations blmut WHERE
        iv.baseline_isolate_name = blmut.isolate_name AND
        mut.gene = blmut.gene AND
        mut.position = blmut.position AND
        mut.amino_acid = blmut.amino_acid AND
        EXISTS (
          SELECT 1 FROM resistance_mutations drms WHERE
            mut.gene = drms.gene AND
            mut.position = drms.position AND
            mut.amino_acid = drms.amino_acid
        )
    ) AS is_baseline_drm
  FROM invitro_selection iv
  INNER JOIN mutations mut ON
    iv.isolate_name = mut.isolate_name
  WHERE NOT EXISTS (
    SELECT 1 FROM mutations blmut WHERE
      iv.baseline_isolate_name = blmut.isolate_name AND
      mut.gene = blmut.gene AND
      mut.position = blmut.position AND
      mut.amino_acid = blmut.amino_acid AND
      NOT EXISTS (
        SELECT 1 FROM resistance_mutations drms WHERE
          mut.gene = drms.gene AND
          mut.position = drms.position AND
          mut.amino_acid = drms.amino_acid
      )
  );
