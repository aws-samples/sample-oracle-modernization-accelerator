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
import java.util.Date;

public class GasPricePeriodDTO implements Serializable {
  private Date loggedDate;
  private Double loggedPrice;
  private Date periodStart;
  private Date periodGroup;

  // Getters and Setters
  public Date getLoggedDate() {
    return loggedDate;
  }

  public void setLoggedDate(Date loggedDate) {
    this.loggedDate = loggedDate;
  }

  public Double getLoggedPrice() {
    return loggedPrice;
  }

  public void setLoggedPrice(Double loggedPrice) {
    this.loggedPrice = loggedPrice;
  }

  public Date getPeriodStart() {
    return periodStart;
  }

  public void setPeriodStart(Date periodStart) {
    this.periodStart = periodStart;
  }

  public Date getPeriodGroup() {
    return periodGroup;
  }

  public void setPeriodGroup(Date periodGroup) {
    this.periodGroup = periodGroup;
  }
}
