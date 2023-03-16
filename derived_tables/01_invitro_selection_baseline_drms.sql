INSERT INTO invitro_selection_baseline_drms
  SELECT iv.ref_name, iv.isolate_name, gene, position, amino_acid
    FROM invitro_selection iv
    INNER JOIN mutations mut ON
      iv.baseline_isolate_name = mut.isolate_name
    WHERE EXISTS (
      SELECT 1 FROM resistance_mutations drms WHERE
        mut.gene = drms.gene AND
        mut.position = drms.position AND
        mut.amino_acid = drms.amino_acid
    );
