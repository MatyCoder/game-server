from par import parse_par_file

config = parse_par_file('etc/local.par')

if config['General.UVLOOP']:
    import uvloop
    uvloop.install()
