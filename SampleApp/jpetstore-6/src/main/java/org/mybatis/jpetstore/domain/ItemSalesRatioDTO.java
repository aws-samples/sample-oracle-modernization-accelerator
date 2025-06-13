/*
 *    Copyright 2010-2025 the original author or authors.
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *       https://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */
package org.mybatis.jpetstore.domain;

import java.io.Serializable;

public class ItemSalesRatioDTO implements Serializable {
  private String grp;
  private String item;
  private String name;
  private Integer qty;
  private Integer rnk;
  private Double gPct;
  private Double tPct;

  // Getters and Setters
  public String getGrp() {
    return grp;
  }

  public void setGrp(String grp) {
    this.grp = grp;
  }

  public String getItem() {
    return item;
  }

  public void setItem(String item) {
    this.item = item;
  }

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public Integer getQty() {
    return qty;
  }

  public void setQty(Integer qty) {
    this.qty = qty;
  }

  public Integer getRnk() {
    return rnk;
  }

  public void setRnk(Integer rnk) {
    this.rnk = rnk;
  }

  public Double getGPct() {
    return gPct;
  }

  public void setGPct(Double gPct) {
    this.gPct = gPct;
  }

  public Double getTPct() {
    return tPct;
  }

  public void setTPct(Double tPct) {
    this.tPct = tPct;
  }
}
