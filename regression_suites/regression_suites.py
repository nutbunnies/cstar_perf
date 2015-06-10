import datetime
from util import get_tagged_releases, get_branches
from cstar_perf.frontend.client.schedule import Scheduler

CSTAR_SERVER = "cstar.datastax.com"

def create_baseline_config(title=None):
    """Creates a config for testing the latest dev build(s) against stable and oldstable"""
    
    dev_revisions = ['apache/trunk'] + get_branches()[:2]
    stable = get_tagged_releases('stable')[0]
    oldstable = get_tagged_releases('oldstable')[0]

    config = {}

    config['revisions'] = revisions = []
    for r in dev_revisions:
        revisions.append({'revision': r, 'label': r +' (dev)'})
    revisions.append({'revision': stable, 'label': stable+' (stable)'})
    revisions.append({'revision': oldstable, 'label': oldstable+' (oldstable)'})
    for r in revisions:
        r['options'] = {'use_vnodes': True}
        r['java_home'] = "~/fab/jvms/jdk1.7.0_71" if 'oldstable' in r['label'] else "~/fab/jvms/jdk1.8.0_45"

    config['title'] = 'Jenkins C* regression suite - {}'.format(datetime.datetime.now().strftime("%Y-%m-%d"))

    if title is not None:
        config['title'] += ' - {title}'.format(title=title)

    return config

def test_simple_profile(title='Read/Write', cluster='blade_11', load_rows=65000000, read_rows=65000000, threads=300, yaml=None):
    """Test the basic stress profile with default C* settings"""
    config = create_baseline_config(title)
    config['cluster'] = cluster
    config['operations'] = [
        {'operation':'stress',
         'command': 'write n={load_rows} -rate threads={threads}'.format(**locals())},
        {'operation':'stress',
         'command': 'read n={read_rows} -rate threads={threads}'.format(**locals())},
        {'operation':'stress',
         'command': 'read n={read_rows} -rate threads={threads}'.format(**locals())}
    ]
    if yaml:
        config['yaml'] = yaml

    scheduler = Scheduler(CSTAR_SERVER)
    scheduler.schedule(config)

def compaction_profile(title='Compaction', cluster='blade_11', rows=65000000, threads=300):
    config = create_baseline_config(title)
    config['cluster'] = cluster
    config['operations'] = [
        {'operation': 'stress',
         'command': 'write n={rows} -rate threads={threads}'.format(rows=rows, threads=threads)},
        {'operation': 'nodetool',
         'command': 'flush'},
        {'operation': 'nodetool',
         'command': 'compact'},
        {'operation': 'stress',
         'command': 'read n={rows} -rate threads={threads}'.format(rows=rows, threads=threads)},
        {'operation': 'stress',
         'command': 'read n={rows} -rate threads={threads}'.format(rows=rows, threads=threads)}]

    scheduler = Scheduler(CSTAR_SERVER)
    scheduler.schedule(config)

def test_compaction_profile():
    compaction_profile()

def repair_profile(title='Repair', cluster='blade_11', rows=65000000, threads=300):
    config = create_baseline_config()
    config['cluster'] = cluster
    config['operations'] = [
        {'operation': 'stress',
         'command': 'write n={rows} -rate threads={threads}'.format(rows=rows, threads=threads)},
        {'operation': 'nodetool',
         'command': 'flush'},
        {'operation': 'nodetool',
         'command': 'repair'},
        {'operation': 'stress',
         'command': 'read n={rows} -rate threads={threads}'.format(rows=rows, threads=threads)},
        {'operation': 'stress',
         'command': 'read n={rows} -rate threads={threads}'.format(rows=rows, threads=threads)}]

    scheduler = Scheduler(CSTAR_SERVER)
    scheduler.schedule(config)

def test_repair_profile():
    repair_profile()

def test_commitlog_sync_settings():
    yaml = '\n'.join(['commitlog_sync: batch',
                      'commitlog_sync_batch_window_in_ms: 50',
                      'commitlog_sync_period_in_ms: null',
                      'concurrent_writes: 64'])
    test_simple_profile(title='Batch Commitlog', yaml=yaml)
