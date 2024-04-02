drop database if exists imgbDB;

create database if not exists imgbDB
	default character set utf8mb4
	default collate utf8mb4_0900_ai_ci;

use imgbDB;

create table if not exists images(
imageID int auto_increment primary key,
Img LONGBLOB,
encryptedImgcustomers LONGBLOB,
keyImg BLOB,
decryptedImg LONGBLOB
);

-- drop table images;

