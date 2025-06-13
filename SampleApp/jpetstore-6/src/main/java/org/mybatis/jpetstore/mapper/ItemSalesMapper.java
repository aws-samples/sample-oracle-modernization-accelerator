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
import org.mybatis.jpetstore.domain.ItemSalesRatioDTO;

public interface ItemSalesMapper {
  @Select("SELECT g.grp, g.item, g.name, g.qty, g.rnk, " + "       ROUND(g.g_pct, 1) as g_pct, "
      + "       ROUND(g.t_pct, 1) as t_pct " + "FROM ( "
      + "    SELECT i.grp, i.item, MAX(i.name) name, SUM(s.qty) qty, " + "           RANK() OVER ( "
      + "               PARTITION BY i.grp " + "               ORDER BY SUM(s.qty) DESC " + "           ) rnk, "
      + "           100 * RATIO_TO_REPORT(SUM(s.qty)) OVER (PARTITION BY i.grp) g_pct, "
      + "           100 * RATIO_TO_REPORT(SUM(s.qty)) OVER () t_pct " + "    FROM items i "
      + "    JOIN sales s ON s.item = i.item " + "    WHERE s.mth BETWEEN '2014-01-01' AND '2014-12-01' "
      + "    GROUP BY i.grp, i.item " + ") g " + "WHERE g.rnk <= 3 " + "ORDER BY g.grp, g.rnk, g.item")
  List<ItemSalesRatioDTO> getItemSalesRatio();
}
