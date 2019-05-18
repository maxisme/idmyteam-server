SET FOREIGN_KEY_CHECKS=0;
CREATE TABLE `Logs` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `type` varchar(200) NOT NULL,
  `method` varchar(200) NOT NULL,
  `yaxis` varchar(200) NOT NULL DEFAULT '',
  `name` varchar(200) NOT NULL,
  `value` float NOT NULL,
  `username` varchar(64) NOT NULL DEFAULT '',
  `time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;
CREATE TABLE `Login` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `time` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `username` varchar(64) CHARACTER SET utf8 NOT NULL DEFAULT '',
  `ip` varchar(100) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  KEY `username` (`username`),
  CONSTRAINT `Login_ibfk_1` FOREIGN KEY (`username`) REFERENCES `Accounts` (`username`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
CREATE TABLE `IP` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `pub` varchar(100) COLLATE utf8mb4_bin DEFAULT NULL,
  `local` varchar(100) COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE `Features` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `class` int(11) NOT NULL,
  `features` varchar(2000) NOT NULL DEFAULT '',
  `type` enum('MANUAL','MODEL') DEFAULT NULL,
  `score` float NOT NULL DEFAULT '0',
  `username` varchar(64) NOT NULL DEFAULT '',
  `create_dttm` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `new` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `account_username` (`username`),
  CONSTRAINT `Features_ibfk_1` FOREIGN KEY (`username`) REFERENCES `Accounts` (`username`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;
CREATE TABLE `Accounts` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `email` varchar(255) NOT NULL DEFAULT '',
  `confirmed_email` timestamp NULL DEFAULT NULL,
  `email_confirm_token` varchar(200) DEFAULT NULL,
  `password_reset_token` varchar(200) DEFAULT NULL,
  `password` varchar(64) NOT NULL DEFAULT '',
  `credentials` varchar(200) NOT NULL DEFAULT '' COMMENT 'encrypted by php',
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `num_classifications` int(11) NOT NULL DEFAULT '0',
  `local_ip` varchar(50) DEFAULT NULL,
  `max_train_imgs_per_hr` int(11) NOT NULL DEFAULT '60',
  `last_upload` varchar(100) NOT NULL DEFAULT '0',
  `upload_retry_limit` float NOT NULL DEFAULT '0.5' COMMENT 'seconds',
  `allow_storage` tinyint(1) NOT NULL DEFAULT '0',
  `is_training` tinyint(1) DEFAULT NULL,
  `max_class_num` int(11) NOT NULL DEFAULT '5',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;
SET FOREIGN_KEY_CHECKS=1;