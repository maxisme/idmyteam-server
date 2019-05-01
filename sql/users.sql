-- admin user
GRANT ALL PRIVILEGES ON idmyteam.* TO 'idmyteam'@'localhost' IDENTIFIED BY 'vg1zSr0Ug9ptQyvtbmRCGXYhl1baVw2qxWcUenlG!';

-- server user
GRANT INSERT, SELECT, DELETE, UPDATE ON idmyteam.* TO 'idmyteam_user'@'localhost' IDENTIFIED BY 'pPArS16chi9zMBGEqPNVcaY4NodtSu5pSK5rWFFq!';
