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

create table SUPPLIER (
    suppid int not null,
    name varchar2(80) null,
    status varchar2(2) not null,
    addr1 varchar2(80) null,
    addr2 varchar2(80) null,
    city varchar2(80) null,
    state varchar2(80) null,
    zip varchar2(5) null,
    phone varchar2(80) null,
    constraint pk_supplier primary key (suppid)
);

create table SIGNON (
    username varchar2(25) not null,
    password varchar2(25) not null,
    constraint pk_signon primary key (username)
);

create table ACCOUNT (
    userid varchar2(80) not null,
    email varchar2(80) not null,
    firstname varchar2(80) not null,
    lastname varchar2(80) not null,
    status varchar2(2) null,
    addr1 varchar2(80) not null,
    addr2 varchar2(40) null,
    city varchar2(80) not null,
    state varchar2(80) not null,
    zip varchar2(20) not null,
    country varchar2(20) not null,
    phone varchar2(80) not null,
    constraint pk_account primary key (userid)
);

create table PROFILE (
    userid varchar2(80) not null,
    langpref varchar2(80) not null,
    favcategory varchar2(30),
    mylistopt int,
    banneropt int,
    constraint pk_profile primary key (userid)
);

create table BANNERDATA (
    favcategory varchar2(80) not null,
    bannername varchar2(255) null,
    constraint pk_bannerdata primary key (favcategory)
);

create table ORDERS (
    orderid int not null,
    userid varchar2(80) not null,
    orderdate date not null,
    shipaddr1 varchar2(80) not null,
    shipaddr2 varchar2(80) null,
    shipcity varchar2(80) not null,
    shipstate varchar2(80) not null,
    shipzip varchar2(20) not null,
    shipcountry varchar2(20) not null,
    billaddr1 varchar2(80) not null,
    billaddr2 varchar2(80) null,
    billcity varchar2(80) not null,
    billstate varchar2(80) not null,
    billzip varchar2(20) not null,
    billcountry varchar2(20) not null,
    courier varchar2(80) not null,
    totalprice number(10,2) not null,
    billtofirstname varchar2(80) not null,
    billtolastname varchar2(80) not null,
    shiptofirstname varchar2(80) not null,
    shiptolastname varchar2(80) not null,
    creditcard varchar2(80) not null,
    exprdate varchar2(7) not null,
    cardtype varchar2(80) not null,
    locale varchar2(80) not null,
    constraint pk_orders primary key (orderid)
);

create table ORDERSTATUS (
    orderid int not null,
    linenum int not null,
    timestamp date not null,
    status varchar2(2) not null,
    constraint pk_orderstatus primary key (orderid, linenum)
);

create table LINEITEM (
    orderid int not null,
    linenum int not null,
    itemid varchar2(10) not null,
    quantity int not null,
    unitprice number(10,2) not null,
    constraint pk_lineitem primary key (orderid, linenum)
);

create table CATEGORY (
    catid varchar2(10) not null,
    name varchar2(80) null,
    descn varchar2(255) null,
    constraint pk_category primary key (catid)
);

create table PRODUCT (
    productid varchar2(10) not null,
    category varchar2(10) not null,
    name varchar2(80) null,
    descn varchar2(255) null,
    constraint pk_product primary key (productid),
    constraint fk_product_1 foreign key (category)
    references CATEGORY (catid)
);

create index PRODUCTCAT on PRODUCT (category);
create index PRODUCTNAME on PRODUCT (name);

create table ITEM (
    itemid varchar2(10) not null,
    productid varchar2(10) not null,
    listprice number(10,2) null,
    unitcost number(10,2) null,
    supplier int null,
    status varchar2(2) null,
    attr1 varchar2(80) null,
    attr2 varchar2(80) null,
    attr3 varchar2(80) null,
    attr4 varchar2(80) null,
    attr5 varchar2(80) null,
    constraint pk_item primary key (itemid),
    constraint fk_item_1 foreign key (productid)
    references PRODUCT (productid),
    constraint fk_item_2 foreign key (supplier)
    references SUPPLIER (suppid)
);

create index ITEMPROD on ITEM (productid);

create table INVENTORY (
    itemid varchar2(10) not null,
    qty int not null,
    constraint pk_inventory primary key (itemid)
);

CREATE TABLE SEQUENCE (
    name varchar2(30) not null,
    nextid int not null,
    constraint pk_sequence primary key (name)
);