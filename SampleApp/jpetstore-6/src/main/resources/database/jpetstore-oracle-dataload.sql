--
--    Copyright 2010-2025 the original author or authors.
--
--    Licensed under the Apache License, Version 2.0 (the "License");
--    you may not use this file except in compliance with the License.
--    You may obtain a copy of the License at
--
--       https://www.apache.org/licenses/LICENSE-2.0
--
--    Unless required by applicable law or agreed to in writing, software
--    distributed under the License is distributed on an "AS IS" BASIS,
--    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
--    See the License for the specific language governing permissions and
--    limitations under the License.
--

INSERT INTO SEQUENCE VALUES('ordernum', 1000);
INSERT INTO SIGNON VALUES('j2ee','j2ee');
INSERT INTO SIGNON VALUES('ACID','ACID');

INSERT INTO ACCOUNT VALUES('j2ee','yourname@yourdomain.com','ABC', 'XYX', 'OK', '901 San Antonio Road', 'MS UCUP02-206', 'Palo Alto', 'CA', '94303', 'USA', '555-555-5555');
INSERT INTO ACCOUNT VALUES('ACID','acid@yourdomain.com','ABC', 'XYX', 'OK', '901 San Antonio Road', 'MS UCUP02-206', 'Palo Alto', 'CA', '94303', 'USA', '555-555-5555');

INSERT INTO PROFILE VALUES('j2ee','english','DOGS',1,1);
INSERT INTO PROFILE VALUES('ACID','english','CATS',1,1);

INSERT INTO BANNERDATA VALUES ('FISH','');
INSERT INTO BANNERDATA VALUES ('CATS','');
INSERT INTO BANNERDATA VALUES ('DOGS','');
INSERT INTO BANNERDATA VALUES ('REPTILES','');
INSERT INTO BANNERDATA VALUES ('BIRDS','');

INSERT INTO CATEGORY VALUES ('FISH','Fish',' Fish');
INSERT INTO CATEGORY VALUES ('DOGS','Dogs',' Dogs');
INSERT INTO CATEGORY VALUES ('REPTILES','Reptiles',' Reptiles');
INSERT INTO CATEGORY VALUES ('CATS','Cats',' Cats');
INSERT INTO CATEGORY VALUES ('BIRDS','Birds',' Birds');

INSERT INTO PRODUCT VALUES ('FI-SW-01','FISH','Angelfish','Salt Water fish from Australia');
INSERT INTO PRODUCT VALUES ('FI-SW-02','FISH','Tiger Shark','Salt Water fish from Australia');
INSERT INTO PRODUCT VALUES ('FI-FW-01','FISH', 'Koi','Fresh Water fish from Japan');
INSERT INTO PRODUCT VALUES ('FI-FW-02','FISH', 'Goldfish','Fresh Water fish from China');
INSERT INTO PRODUCT VALUES ('K9-BD-01','DOGS','Bulldog','Friendly dog from England');
INSERT INTO PRODUCT VALUES ('K9-PO-02','DOGS','Poodle','Cute dog from France');
INSERT INTO PRODUCT VALUES ('K9-DL-01','DOGS', 'Dalmation','Great dog for a Fire Station');
INSERT INTO PRODUCT VALUES ('K9-RT-01','DOGS', 'Golden Retriever','Great family dog');
INSERT INTO PRODUCT VALUES ('K9-RT-02','DOGS', 'Labrador Retriever','Great hunting dog');
INSERT INTO PRODUCT VALUES ('K9-CW-01','DOGS', 'Chihuahua','Great companion dog');
INSERT INTO PRODUCT VALUES ('RP-SN-01','REPTILES','Rattlesnake','Doubles as a watch dog');
INSERT INTO PRODUCT VALUES ('RP-LI-02','REPTILES','Iguana','Friendly green friend');
INSERT INTO PRODUCT VALUES ('FL-DSH-01','CATS','Manx','Great for reducing mouse populations');
INSERT INTO PRODUCT VALUES ('FL-DLH-02','CATS','Persian','Friendly house cat, doubles as a princess');
INSERT INTO PRODUCT VALUES ('AV-CB-01','BIRDS','Amazon Parrot','Great companion for up to 75 years');
INSERT INTO PRODUCT VALUES ('AV-SB-02','BIRDS','Finch','Great stress reliever');

INSERT INTO SUPPLIER VALUES (1,'XYZ Pets','AC','600 Avon Way','','Los Angeles','CA','94024','212-947-0797');
INSERT INTO SUPPLIER VALUES (2,'ABC Pets','AC','700 Abalone Way','','San Francisco ','CA','94024','415-947-0797');


INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-1','FI-SW-01',16.50,10.00,1,'P','Large');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-2','FI-SW-01',16.50,10.00,1,'P','Small');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-3','FI-SW-02',18.50,12.00,1,'P','Toothless');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-4','FI-FW-01',18.50,12.00,1,'P','Spotted');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-5','FI-FW-01',18.50,12.00,1,'P','Spotless');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-6','K9-BD-01',18.50,12.00,1,'P','Male Adult');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-7','K9-BD-01',18.50,12.00,1,'P','Female Puppy');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-8','K9-PO-02',18.50,12.00,1,'P','Male Puppy');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-9','K9-DL-01',18.50,12.00,1,'P','Spotless Male Puppy');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-10','K9-DL-01',18.50,12.00,1,'P','Spotted Adult Female');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-11','RP-SN-01',18.50,12.00,1,'P','Venomless');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-12','RP-SN-01',18.50,12.00,1,'P','Rattleless');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-13','RP-LI-02',18.50,12.00,1,'P','Green Adult');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-14','FL-DSH-01',58.50,12.00,1,'P','Tailless');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-15','FL-DSH-01',23.50,12.00,1,'P','With tail');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-16','FL-DLH-02',93.50,12.00,1,'P','Adult Female');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-17','FL-DLH-02',93.50,12.00,1,'P','Adult Male');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-18','AV-CB-01',193.50,92.00,1,'P','Adult Male');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-19','AV-SB-02',15.50, 2.00,1,'P','Adult Male');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-20','FI-FW-02',5.50, 2.00,1,'P','Adult Male');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-21','FI-FW-02',5.29, 1.00,1,'P','Adult Female');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-22','K9-RT-02',135.50, 100.00,1,'P','Adult Male');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-23','K9-RT-02',145.49, 100.00,1,'P','Adult Female');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-24','K9-RT-02',255.50, 92.00,1,'P','Adult Male');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-25','K9-RT-02',325.29, 90.00,1,'P','Adult Female');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-26','K9-CW-01',125.50, 92.00,1,'P','Adult Male');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-27','K9-CW-01',155.29, 90.00,1,'P','Adult Female');
INSERT INTO  ITEM (itemid, productid, listprice, unitcost, supplier, status, attr1) VALUES('EST-28','K9-RT-01',155.29, 90.00,1,'P','Adult Female');

INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-1',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-2',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-3',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-4',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-5',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-6',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-7',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-8',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-9',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-10',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-11',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-12',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-13',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-14',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-15',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-16',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-17',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-18',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-19',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-20',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-21',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-22',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-23',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-24',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-25',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-26',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-27',10000);
INSERT INTO INVENTORY (itemid, qty ) VALUES ('EST-28',10000);