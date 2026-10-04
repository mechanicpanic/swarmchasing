import polars as pl
R = pl.read_csv('c29_signatures.csv'); K = pl.read_csv('c29_labelkinds.csv')
T = pl.read_parquet('c29_authored_targets.parquet').sort('seq')
# label reuse across sessions (sessions = >10 min gap)
T = T.with_columns((pl.col('time').diff().over('sig').dt.total_seconds().fill_null(0) > 600).cum_sum().over('sig').alias('sess'))
reuse = T.group_by('sig', 'label').agg(pl.col('sess').n_unique().alias('k')).group_by('sig').agg((pl.col('k') > 1).sum().alias('labels_reused_across_sessions'))
X = R.join(K.drop('n'), on='sig').join(reuse, on='sig')
X = X.with_columns(
    pl.when((pl.col('conc_1s') > 0) | (pl.col('p_more') < 0.05)).then(pl.lit('shared'))
      .when(pl.col('p_fewer') < 0.05).then(pl.lit('rotation'))
      .when(pl.col('multi_sessions') == 0).then(pl.lit('untestable'))
      .when(pl.col('interleaved_sessions') == 0).then(pl.lit('rotation'))
      .otherwise(pl.lit('mixed')).alias('class'),
    pl.when(pl.col('p_fewer') < 0.05).then(pl.lit('clustered<null'))
      .when(pl.col('multi_sessions') == 0).then(pl.lit('one save per session'))
      .when(pl.col('interleaved_sessions') == 0).then(pl.lit('contiguous'))
      .otherwise(pl.lit('interleaved~null')).alias('why'),
    pl.when(pl.col('throwaway') >= pl.col('borrowed')).then(pl.lit('self-made')).otherwise(pl.lit('borrowed')).alias('label_source'))
X.write_csv('c29_classified.csv')
print(X['class'].value_counts(), X['why'].value_counts(), X['label_source'].value_counts())
print(X.group_by('class', 'label_source').len().sort('class'))
print('total conc_1s', X['conc_1s'].sum(), 'conc_60s', X['conc_60s'].sum(), 'labels reused across sessions (sum)', X['labels_reused_across_sessions'].sum(),
      'sigs with any reuse', (X['labels_reused_across_sessions'] > 0).sum())
print('sigs where label changes every save within sessions', X['label_changes_every_save'].sum(), '/', X.height)
print('saves', X['saves'].sum(), 'sessions', X['sessions'].sum(), 'multi-label sessions', X['multi_label_sessions'].sum())
print('informative cells median', X['informative_cells'].median(), 'sigs with <=2 informative cells', (X['informative_cells'] <= 2).sum())
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_cols(30)
print(X.select('sig', 'labels', 'saves', 'sessions', 'max_labels_in_session', 'conc_1s', 'conc_60s', 'interleaved_sessions', 'runs_real', 'runs_null_mean', 'p_fewer', 'p_more', 'own', 'throwaway', 'borrowed', 'copies', 'class', 'why', 'label_source').head(60))
