# ************************************************************
# Sequel Pro SQL dump
# Version 4541
#
# http://www.sequelpro.com/
# https://github.com/sequelpro/sequelpro
#
# Host: 127.0.0.1 (MySQL 5.7.22-0ubuntu0.17.10.1)
# Database: ID My Team
# Generation Time: 2018-04-29 21:35:08 +0000
# ************************************************************


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


# Dump of table Accounts
# ------------------------------------------------------------

CREATE TABLE `Accounts` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `email` varchar(255) NOT NULL DEFAULT '',
  `password` varchar(64) NOT NULL DEFAULT '',
  `credentials` varchar(200) NOT NULL DEFAULT '' COMMENT 'encrypted by php',
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `num_classifications` int(11) NOT NULL DEFAULT '0',
  `local_ip` varchar(50) DEFAULT NULL,
  `model_port` int(11) DEFAULT NULL,
  `last_upload` varchar(100) DEFAULT NULL,
  `last_train` varchar(100) NOT NULL DEFAULT '0',
  `upload_retry_limit` float NOT NULL DEFAULT '0.5' COMMENT 'seconds',
  `allow_storage` tinyint(1) NOT NULL DEFAULT '0',
  `is_training` tinyint(1) DEFAULT NULL,
  `max_class_num` int(11) NOT NULL DEFAULT '5',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;



# Dump of table Features
# ------------------------------------------------------------

CREATE TABLE `Features` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `class` int(11) NOT NULL,
  `features` varchar(3000) NOT NULL DEFAULT '',
  `type` enum('MANUAL','MODEL') DEFAULT NULL,
  `score` float NOT NULL DEFAULT '0',
  `account_username` varchar(64) NOT NULL DEFAULT '',
  `time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `new` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `account_username` (`account_username`),
  CONSTRAINT `Features_ibfk_1` FOREIGN KEY (`account_username`) REFERENCES `Accounts` (`username`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;



# Dump of table IP
# ------------------------------------------------------------

CREATE TABLE `IP` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `pub` varchar(100) COLLATE utf8mb4_bin DEFAULT NULL,
  `local` varchar(100) COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;



# Dump of table Login
# ------------------------------------------------------------

CREATE TABLE `Login` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `time` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `username` varchar(64) CHARACTER SET utf8 NOT NULL DEFAULT '',
  `ip` varchar(100) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  KEY `username` (`username`),
  CONSTRAINT `Login_ibfk_1` FOREIGN KEY (`username`) REFERENCES `Accounts` (`username`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;



# Dump of table Logs
# ------------------------------------------------------------

CREATE TABLE `Logs` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `type` varchar(200) NOT NULL,
  `method` varchar(200) NOT NULL,
  `yaxis` varchar(200) NOT NULL DEFAULT '',
  `name` varchar(200) NOT NULL,
  `value` float NOT NULL,
  `user` varchar(64) NOT NULL DEFAULT '',
  `time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;




--
-- Dumping routines (PROCEDURE) for database 'ID My Team'
--
DELIMITER ;;

# Dump of PROCEDURE has_new_class
# ------------------------------------------------------------

/*!50003 SET SESSION SQL_MODE="ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION"*/;;
/*!50003 CREATE*/ /*!50020 DEFINER=`root`@`localhost`*/ /*!50003 PROCEDURE `has_new_class`(username varchar(64))
BEGIN
	SELECT CASE
	           WHEN Count(y.`class`) > 0 THEN 1
	           ELSE 0
	       END
	FROM
	  (SELECT CLASS
	   FROM Features
	   WHERE account_username = username
	   GROUP BY CLASS) y
	LEFT JOIN
	  (SELECT CLASS
	   FROM Features
	   WHERE NEW = 0
	   AND account_username = username
	   GROUP BY CLASS) x ON x.class = y.`class`
	WHERE x.`class` IS NULL;
END */;;

/*!50003 SET SESSION SQL_MODE=@OLD_SQL_MODE */;;
DELIMITER ;

/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
