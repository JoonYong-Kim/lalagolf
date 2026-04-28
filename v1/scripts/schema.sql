-- LalaGolf managed schema
-- This file is intended for initial database creation, not as a raw dump.
-- The current application stores rounds, aggregated nine-hole summaries,
-- hole-level scores, and shot-by-shot records used by the analytics layer.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `shots`;
DROP TABLE IF EXISTS `holes`;
DROP TABLE IF EXISTS `nines`;
DROP TABLE IF EXISTS `rounds`;

CREATE TABLE `rounds` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `gcname` VARCHAR(50) DEFAULT NULL,
  `player` VARCHAR(50) DEFAULT NULL,
  `coplayers` VARCHAR(100) DEFAULT NULL,
  `playdate` DATETIME NOT NULL,
  `score` FLOAT DEFAULT NULL,
  `gir` FLOAT DEFAULT NULL,
  `raw_data` LONGTEXT DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_rounds_playdate` (`playdate`),
  KEY `idx_rounds_playdate` (`playdate`),
  KEY `idx_rounds_gcname` (`gcname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `nines` (
  `roundid` INT NOT NULL,
  `ordnum` INT NOT NULL,
  `course` VARCHAR(50) DEFAULT NULL,
  `par` INT DEFAULT NULL,
  `score` INT DEFAULT NULL,
  `gir` FLOAT DEFAULT NULL,
  PRIMARY KEY (`roundid`, `ordnum`),
  CONSTRAINT `fk_nines_roundid`
    FOREIGN KEY (`roundid`) REFERENCES `rounds` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `holes` (
  `roundid` INT NOT NULL,
  `holenum` INT NOT NULL,
  `par` INT DEFAULT NULL,
  `score` INT DEFAULT NULL,
  `putt` INT DEFAULT NULL,
  PRIMARY KEY (`roundid`, `holenum`),
  KEY `idx_holes_roundid_holenum` (`roundid`, `holenum`),
  CONSTRAINT `fk_holes_roundid`
    FOREIGN KEY (`roundid`) REFERENCES `rounds` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `shots` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `roundid` INT NOT NULL,
  `holenum` INT DEFAULT NULL,
  `club` CHAR(2) DEFAULT NULL,
  `feelgrade` CHAR(1) DEFAULT NULL,
  `retgrade` CHAR(1) DEFAULT NULL,
  `concede` TINYINT(1) DEFAULT NULL,
  `score` INT DEFAULT NULL,
  `penalty` CHAR(2) DEFAULT NULL,
  `retplace` CHAR(1) DEFAULT NULL,
  `shotplace` CHAR(1) DEFAULT NULL,
  `distance` FLOAT DEFAULT NULL,
  `error` FLOAT DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_shots_roundid` (`roundid`),
  KEY `idx_shots_roundid_holenum` (`roundid`, `holenum`),
  CONSTRAINT `fk_shots_roundid`
    FOREIGN KEY (`roundid`) REFERENCES `rounds` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
