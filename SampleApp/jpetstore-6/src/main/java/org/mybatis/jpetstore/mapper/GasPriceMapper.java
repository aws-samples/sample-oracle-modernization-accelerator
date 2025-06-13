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
package org.mybatis.jpetstore.mapper;

import java.util.List;

import org.apache.ibatis.annotations.Select;
import org.mybatis.jpetstore.domain.GasPricePeriodDTO;

public interface GasPriceMapper {
  @Select("SELECT logged_date, " + "       logged_price, " + "       period_start, "
      + "       LAST_VALUE(period_start IGNORE NULLS) OVER ( " + "           ORDER BY logged_date "
      + "           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW " + "       ) period_group " + "FROM ( "
      + "    SELECT logged_date, " + "           logged_price, "
      + "           CASE LAG(logged_price) OVER (ORDER BY logged_date) " + "               WHEN logged_price THEN NULL "
      + "               ELSE logged_date " + "           END period_start " + "    FROM gas_price_log " + ") "
      + "ORDER BY logged_date")
  List<GasPricePeriodDTO> getGasPricePeriods();
}
