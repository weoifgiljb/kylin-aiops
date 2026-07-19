CREATE DATABASE IF NOT EXISTS ops_demo;
CREATE USER IF NOT EXISTS 'ops_demo'@'%' IDENTIFIED BY 'ops_demo_password';
GRANT SELECT ON ops_demo.* TO 'ops_demo'@'%';
CREATE USER IF NOT EXISTS 'ops_fault'@'%' IDENTIFIED BY 'ops_fault_password';
GRANT USAGE ON *.* TO 'ops_fault'@'%';
FLUSH PRIVILEGES;
