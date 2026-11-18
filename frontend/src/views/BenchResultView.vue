<template>
  <div class="bench-result">
    <!-- 顶部信息栏 -->
    <header class="br-head">
      <div class="br-title">
        <span class="br-name">{{ job.name || '批量测试结果' }}</span>
        <a-tag v-if="job.status" size="small" :color="statusColor(job.status)">{{ statusText(job.status) }}</a-tag>
        <span class="br-meta">
          <span v-if="job.dataset_name">测试集 {{ job.dataset_name }}</span>
          <span v-if="job.total">成功 <b class="ok">{{ job.success }}</b> / 失败
            <b :class="{ err: job.fail > 0 }">{{ job.fail }}</b></span>
          <span v-if="job.concurrency">并发 {{ job.concurrency }}</span>
          <span v-if="job.stats?.avg_ms">avg {{ job.stats.avg_ms }}ms</span>
          <span v-if="job.stats?.p95_ms">p95 {{ job.stats.p95_ms }}ms</span>
          <span v-if="job.stats?.ttft_avg_ms">TTFT {{ job.stats.ttft_avg_ms }}ms</span>
          <span class="muted">{{ job.created_at }}</span>
        </span>
      </div>
      <div class="br-actions">
        <a-button size="small" @click="reload">
          <template #icon><icon-refresh /></template>刷新
        </a-button>
        <a-button size="small" @click="downloadRawCsv">下载原始文件</a-button>
        <a-button size="small" type="primary" @click="exportView">下载最终结果</a-button>
        <a-button size="small" @click="closeWindow">关闭</a-button>
      </div>
    </header>

    <!-- 格式工具条：左侧清除格式（文字在上图标在下），中间上排字体/字号 + 下排字形与颜色，右侧两组对齐 -->
    <div class="br-fmtbar">
      <button type="button" class="br-fmt-tall" title="清除所选单元格的格式" @click="clearFormat()">
        <span class="br-tall-text">清除格式</span>
        <icon-eraser />
      </button>

      <span class="br-fmt-sep"></span>

      <div class="br-fmt-main">
        <div class="br-fmt-row">
          <a-select v-model="fontSel" size="mini" style="width: 120px;min-width: 120px;max-width: 120px;"
            class="br-fg-font" placement="bottom" placeholder="默认字体" title="字体" @change="onPickFont">
            <a-option :value="''">默认字体</a-option>
            <a-option v-for="font in font_list" :key="font" :value="font">{{ font }}</a-option>
          </a-select>
          <a-select v-model="sizeSel" size="mini" class="br-fg-size" placement="bottom" title="字号" @change="onPickSize">
            <a-option v-for="sz in [10, 11, 12, 14, 16, 18, 20]" :key="sz" :value="sz">{{ sz }}</a-option>
          </a-select>
        </div>

        <div class="br-fmt-row">
          <button type="button" class="br-fmt-ic" :class="{ 'is-on': selHasBold }" title="加粗"
            @click="toggleStyle('bold')">
            <icon-bold />
          </button>
          <button type="button" class="br-fmt-ic" :class="{ 'is-on': selHasStrike }" title="删除线"
            @click="toggleStyle('strike')">
            <icon-strikethrough />
          </button>
          <button type="button" class="br-fmt-ic" :class="{ 'is-on': selHasItalic }" title="斜体"
            @click="toggleStyle('italic')">
            <icon-italic />
          </button>
          <button type="button" class="br-fmt-ic" :class="{ 'is-on': selHasUnderline }" title="下划线"
            @click="toggleStyle('underline')">
            <icon-underline />
          </button>

          <div class="br-fmt-dd br-fg-fcolor">
            <button type="button" class="br-fmt-ic br-fmt-color" :class="{ 'is-on': palette === 'font' }" title="字体颜色"
              @mousedown.stop @click.stop="togglePalette('font')">
              <icon-font-colors />
              <span class="br-color-bar" :style="{ background: fontColor }"></span>
            </button>
            <div v-if="palette === 'font'" class="br-palette" @mousedown.stop @click.stop>
              <div class="br-pal-grid">
                <button v-for="c in PALETTE" :key="'f' + c" type="button" class="br-pal-sw"
                  :class="{ 'is-cur': c.toLowerCase() === fontColor.toLowerCase() }" :style="{ background: c }"
                  :title="c" @click="pickColor('font', c)" />
              </div>
              <div class="br-pal-title">最近使用</div>
              <div class="br-pal-grid br-pal-recent">
                <button v-for="c in recentColors" :key="'rf' + c" type="button" class="br-pal-sw"
                  :style="{ background: c }" :title="c" @click="pickColor('font', c)" />
                <span v-if="!recentColors.length" class="br-pal-empty">暂无</span>
              </div>
              <label class="br-pal-more">
                <span class="br-pal-dot"></span>更多颜色
                <input type="color" :value="fontColor" @input="onMoreColor('font', $event)" />
              </label>
            </div>
          </div>

          <div class="br-fmt-dd br-fg-bcolor">
            <button type="button" class="br-fmt-ic br-fmt-color" :class="{ 'is-on': palette === 'bg' }" title="单元格颜色"
              @mousedown.stop @click.stop="togglePalette('bg')">
              <icon-bg-colors />
              <span class="br-color-bar" :style="{ background: bgColor }"></span>
            </button>
            <div v-if="palette === 'bg'" class="br-palette" @mousedown.stop @click.stop>
              <div class="br-pal-grid">
                <button v-for="c in PALETTE" :key="'b' + c" type="button" class="br-pal-sw"
                  :class="{ 'is-cur': c.toLowerCase() === bgColor.toLowerCase() }" :style="{ background: c }" :title="c"
                  @click="pickColor('bg', c)" />
              </div>
              <div class="br-pal-title">最近使用</div>
              <div class="br-pal-grid br-pal-recent">
                <button v-for="c in recentColors" :key="'rb' + c" type="button" class="br-pal-sw"
                  :style="{ background: c }" :title="c" @click="pickColor('bg', c)" />
                <span v-if="!recentColors.length" class="br-pal-empty">暂无</span>
              </div>
              <label class="br-pal-more">
                <span class="br-pal-dot"></span>更多颜色
                <input type="color" :value="bgColor" @input="onMoreColor('bg', $event)" />
              </label>
            </div>
          </div>
        </div>
      </div>

      <span class="br-fmt-sep"></span>

      <!-- 对齐：上排垂直对齐，下排水平对齐 -->
      <div class="br-align-grid">
        <a-button type="text" title="顶部对齐" :class="{ 'is-on': selValign === 'top' }" @click="setAlign('valign', 'top')">
          <template #icon>
            <iconToTop />
          </template>
        </a-button>
        <a-button type="text" title="垂直对齐" :class="{ 'is-on': selValign === 'middle' }"
          @click="setAlign('valign', 'middle')">
          <template #icon>
            <iconToMiddle />
          </template>
        </a-button>
        <a-button type="text" title="底部对齐" :class="{ 'is-on': selValign === 'bottom' }"
          @click="setAlign('valign', 'bottom')">
          <template #icon>
            <iconToBottom />
          </template>
        </a-button>
        <a-button type="text" title="向左对齐" :class="{ 'is-on': selHalign === 'left' }"
          @click="setAlign('halign', 'left')">
          <template #icon>
            <iconToLeft />
          </template>
        </a-button>
        <a-button type="text" title="中心对齐" :class="{ 'is-on': selHalign === 'center' }"
          @click="setAlign('halign', 'center')">
          <template #icon>
            <iconToCenter />
          </template>
        </a-button>
        <a-button type="text" title="向右对齐" :class="{ 'is-on': selHalign === 'right' }"
          @click="setAlign('halign', 'right')">
          <template #icon>
            <iconToRight />
          </template>
        </a-button>
      </div>

      <span v-if="targetCells.length" class="br-fmt-hint">
        已选 {{ targetCells.length }} 格<template v-if="selCols.length">（{{ selCols.length }} 列）</template><template
          v-if="selRows.length">（{{ selRows.length }} 行）</template>，Shift 点击可扩选范围
      </span>
      <span v-else class="br-fmt-hint muted">先点选单元格；不选时字体/字号作用于整表</span>
    </div>

    <!-- 表格 -->
    <div ref="wrapRef" class="br-grid-wrap" @scroll="onScroll">
      <div v-if="!ready" class="br-loading">
        <icon-loading class="spin" />正在加载结果…
      </div>
      <div v-else class="br-sheet" :style="{ width: GUTTER_W + totalWidth + 'px' }">
        <!-- 列标（A、B、C…）+ 列名，两层表头，滚动时吸顶 -->
        <div class="br-colhead">
          <div class="br-corner" :class="{ 'is-on': selAll }" title="点击全选整张表" @click.stop="selectAllCells"
            @contextmenu.prevent.stop="openCtx($event, 'all')">{{ nameBoxText }}</div>
          <div class="br-head-main">
            <div class="br-let-row">
              <div v-for="(c, i) in displayColumns" :key="'let-' + c.key" class="br-let"
                :style="{ width: c.width + 'px' }" :class="{ 'is-on': selAll || selCols.includes(c.key) }"
                :title="c.label" @click.stop="onColClick(c, $event)"
                @contextmenu.prevent.stop="openCtx($event, 'col', c)">
                {{ colLetter(i) }}
              </div>
            </div>
            <div class="br-head-row">
              <div v-for="c in displayColumns" :key="c.key" class="br-th" :style="{ width: c.width + 'px' }"
                :class="{ 'is-sorted': sortKey === c.key, 'is-on': selAll || selCols.includes(c.key) }"
                @click="openColumnPanel(c, $event)" @contextmenu.prevent.stop="openCtx($event, 'col', c)">
                <input v-if="c.blank" class="br-th-edit" :value="blankColLabel(c.key)" @mousedown.stop @click.stop
                  @contextmenu.stop @input="onBlankColLabel(c.key, $event)" />
                <span v-else class="br-th-name" :title="c.label">{{ c.label }}</span>
                <icon-caret-up v-if="sortKey === c.key && sortDir === 'asc'" class="br-th-flag" />
                <icon-caret-down v-else-if="sortKey === c.key" class="br-th-flag" />
                <icon-filter v-if="hasFilter(c.key)" class="br-th-flag is-active" />
                <span class="br-resize" @mousedown="startResize($event, c.key, c.width)" @click.stop></span>
              </div>
            </div>
          </div>
        </div>
        <div class="br-body" :style="{ height: visibleRows.length * rowH + 'px' }">
          <!-- 选区外框：单一描边，内部单元格边框隐藏 -->
          <div v-if="selRect" class="br-selbox"
            :style="{ left: selRect.left + 'px', top: selRect.top + 'px', width: selRect.width + 'px', height: selRect.height + 'px' }">
          </div>
          <div v-for="item in windowRows" :key="item.rowNo" class="br-row"
            :class="{ fail: item.isFail, 'has-ann': item.hasAnn, 'is-on': selRows.includes(item.rowNo) }"
            :style="{ height: rowH + 'px', transform: `translateY(${item.idx * rowH}px)` }">
            <div class="br-gutter" :class="{ 'is-on': selRows.includes(item.rowNo) }"
              @click.stop="onRowClick(item, $event)" @contextmenu.prevent.stop="openCtx($event, 'row', null, item)">
              {{ item.idx + 1 }}
            </div>
            <div v-for="c in displayColumns" :key="c.key" class="br-td"
              :style="{ width: c.width + 'px', ...cellCss(item.rowNo, c.key) }"
              :class="{ 'br-td-ann': !!c.annId, 'in-sel': isInSel(item.rowNo, c.key) }"
              @click="onCellClick(item, c.key, $event)" @dblclick.stop="startEdit(item, c)"
              @contextmenu="onCellCtx($event, c, item)">
              <template v-if="isEditing(item.rowNo, c.key)">
                <input v-model="editValue" class="br-cell-edit" @click.stop @blur="commitEdit"
                  @keydown.enter.prevent="commitEdit" @keydown.esc.stop.prevent="cancelEdit" />
              </template>
              <template v-else-if="item.blank || c.blank">
                <span class="br-cell-text">{{ cellText(item, c) }}</span>
              </template>
              <template v-else-if="c.annId">
                <input class="br-ann-input" :value="cellValue(item.rowNo, c.annId)" placeholder="—"
                  @input="onCellInputEvent(item.rowNo, c.annId, $event)" @blur="onCellBlur" />
              </template>
              <template v-else-if="c.wrap">
                <span class="br-cell-text is-wrap" :title="cellText(item, c)">{{ cellText(item, c) }}</span>
                <a-button v-if="cellText(item, c).length > 60" class="br-zoom" size="mini" type="text"
                  @click="openDetail(c.label, cellText(item, c))">
                  <template #icon><icon-eye /></template>
                </a-button>
              </template>
              <template v-else>
                <span class="br-cell-text" :title="cellText(item, c)">{{ cellText(item, c) }}</span>
                <a-button v-if="cellText(item, c).length > 60" class="br-zoom" size="mini" type="text"
                  @click="openDetail(c.label, cellText(item, c))">
                  <template #icon><icon-eye /></template>
                </a-button>
              </template>
            </div>
          </div>
        </div>
        <div v-if="!visibleRows.length && !loading" class="br-empty">
          <a-empty :description="rows.length ? '没有符合筛选条件的行' : '结果文件为空'" />
        </div>
      </div>
    </div>

    <!-- 底部状态栏：选区的计数值 / 求和 / 平均值（非数字单元格按 0 计入） -->
    <div style="display:flex;justify-content:space-between;">
      <div class="br-statusbar">
        <span class="br-st-item">
          共 {{ rows.length }} 行<template v-if="visibleRows.length !== rows.length">，筛选后 {{ visibleRows.length }}
            行</template>
        </span>
        <span v-if="loading" class="br-saving"><icon-loading />加载中…</span>
        <span v-else-if="truncated" class="br-warn" title="可通过「下载结果」查看完整结果">
          <icon-exclamation-circle />结果超过 {{ MAX_ROWS }} 行，仅加载前 {{ MAX_ROWS }} 行
        </span>
        <span v-if="annError" class="br-warn" :title="'标注读取失败：' + annError">
          <icon-exclamation-circle />标注读取失败（请确认后端已重启）
          <a-button size="mini" type="text" @click="loadAnnotations">重试</a-button>
        </span>
        <span v-if="saving" class="br-saving"><icon-loading />保存中…</span>
        <span v-else-if="dirty" class="br-saving">有未保存的标注，稍后自动保存</span>
      </div>
      <div class="br-statusbar">
        <span class="br-st-item">计数值: <b>{{ stat.count }}</b></span>
        <span class="br-st-item">求和: <b>{{ stat.sumText }}</b></span>
        <span class="br-st-item">平均值: <b>{{ stat.avgText }}</b></span>
      </div>
    </div>


    <!-- 右键菜单：列头 / 行号 / 单元格 / 选区 / 全选 统一同一套功能 -->
    <div v-if="ctx.open" class="br-ctx" :style="{ left: ctx.x + 'px', top: ctx.y + 'px' }">
      <div class="br-ctx-item" @click="ctxCopyColumn()"><span>复制整列</span></div>
      <div class="br-ctx-sep"></div>
      <div class="br-ctx-item" @click="ctxInsertRow('up')"><span>向上插入 1 行</span><span
          class="br-ctx-icon"><icon-arrow-up /></span></div>
      <div class="br-ctx-item" @click="ctxInsertRow('down')"><span>向下插入 1 行</span><span
          class="br-ctx-icon"><icon-arrow-down /></span></div>
      <div class="br-ctx-item" @click="ctxInsertCol('left')"><span>向左插入 1 列</span><span
          class="br-ctx-icon"><icon-arrow-left /></span></div>
      <div class="br-ctx-item" @click="ctxInsertCol('right')"><span>向右插入 1 列</span><span
          class="br-ctx-icon"><icon-arrow-right /></span></div>
      <div class="br-ctx-item danger" @click="ctxDeleteRow()"><span>删除此行</span></div>
      <div class="br-ctx-sep"></div>
      <div class="br-ctx-item" @click="ctxSort('asc')"><span>升序排列</span><span
          class="br-ctx-icon"><icon-arrow-up /></span>
      </div>
      <div class="br-ctx-item" @click="ctxSort('desc')"><span>降序排列</span><span
          class="br-ctx-icon"><icon-arrow-down /></span></div>
      <div class="br-ctx-item" @click="ctxFilter()"><span>筛选此列</span><span class="br-ctx-icon"><icon-filter /></span>
      </div>
      <div class="br-ctx-sep"></div>
      <div class="br-ctx-item" @click="ctxWrap()"><span>自动换行</span>
        <span class="br-ctx-sub">{{ selColWrap ? '开' : '关' }}</span>
      </div>
      <div class="br-ctx-item" @click="ctxFitWidth()"><span>列宽自适应</span></div>
      <div class="br-ctx-item" @click="ctxHideColumn()"><span>隐藏此列</span></div>
      <div class="br-ctx-item danger" @click="ctxDeleteColumn()"><span>删除此列</span></div>
      <div class="br-ctx-sep"></div>
      <div class="br-ctx-item" @click="ctxClearFormat()"><span>清除此列格式</span></div>
    </div>

    <!-- 列操作 / 筛选面板（类似飞书表头下拉） -->
    <div v-if="panel.open" class="br-panel" :style="{ left: panel.x + 'px', top: panel.y + 'px' }">
      <div class="br-panel-head">
        <span class="br-panel-col" :title="panel.label">{{ panel.label }}</span>
        <span class="muted">{{ panel.rowCount }} 行</span>
      </div>

      <div class="br-sort-row">
        <button type="button" class="br-sort-btn" :class="{ on: sortKey === panel.key && sortDir === 'asc' }"
          @click="applySort('asc')">
          <icon-arrow-up /> 升序
        </button>
        <button type="button" class="br-sort-btn" :class="{ on: sortKey === panel.key && sortDir === 'desc' }"
          @click="applySort('desc')">
          <icon-arrow-down /> 降序
        </button>
      </div>

      <div class="br-panel-actions">
        <a-switch size="small" :model-value="panelWrap" @change="onWrapChange" />
        <span class="br-wrap-label">自动换行</span>
        <span class="br-panel-spacer"></span>
        <a-button v-if="panel.annId" size="mini" type="text" @click="renamePanelColumn">
          <template #icon><icon-edit /></template>重命名
        </a-button>
        <a-button size="mini" status="danger" type="text" @click="removePanelColumn">
          <template #icon><icon-delete /></template>{{ panel.annId ? '删除该标注列' : '删除此列' }}
        </a-button>
      </div>

      <div class="br-panel-tabs">
        <span class="br-tab" :class="{ on: panelTab === 'value' }" @click="panelTab = 'value'">按值筛选</span>
        <span class="br-tab" :class="{ on: panelTab === 'cond' }" @click="panelTab = 'cond'">按条件筛选</span>
      </div>

      <!-- 按值筛选 -->
      <template v-if="panelTab === 'value'">
        <div class="br-panel-search">
          <a-input v-model="valueSearch" size="small" placeholder="可使用空格分隔多个关键词" allow-clear>
            <template #prefix><icon-search /></template>
          </a-input>
        </div>
        <div class="br-value-list">
          <div class="br-value-row">
            <a-checkbox :model-value="draftAll" @change="onDraftAllChange">全选</a-checkbox>
            <span class="muted">{{ panelValues.length }} 个值</span>
          </div>
          <div v-for="v in visibleValues" :key="v.value" class="br-value-row">
            <a-checkbox :model-value="draftSel.includes(v.value)" @change="() => toggleDraftValue(v.value)">
              <span class="br-value-text" :title="v.value || '（空白）'">{{ v.value || '（空白）' }}</span>
            </a-checkbox>
            <span class="muted">{{ v.count }}</span>
          </div>
          <div v-if="panelOverflow" class="br-value-tip muted">值过多，仅列出前 300 个</div>
        </div>
      </template>

      <!-- 按条件筛选 -->
      <template v-else>
        <div class="br-cond">
          <a-select v-model="draftCond.op" size="small" style="width: 110px">
            <a-option value="contains">包含</a-option>
            <a-option value="notContains">不包含</a-option>
            <a-option value="equals">等于</a-option>
            <a-option value="empty">为空</a-option>
            <a-option value="notEmpty">不为空</a-option>
          </a-select>
          <a-input v-if="draftCond.op !== 'empty' && draftCond.op !== 'notEmpty'" v-model="draftCond.value" size="small"
            placeholder="输入内容" allow-clear />
        </div>
      </template>

      <div class="br-panel-footer">
        <a-button size="mini" type="text" @click="clearPanelFilter">清除筛选</a-button>
        <span class="br-panel-spacer"></span>
        <a-button size="mini" @click="panel.open = false">取消</a-button>
        <a-button size="mini" type="primary" @click="confirmPanel">确认</a-button>
      </div>
    </div>

    <!-- 单元格全文 -->
    <a-drawer v-model:visible="detailOpen" :width="720" title="单元格内容" :footer="false">
      <div class="br-detail">
        <div class="br-detail-head">
          <span class="muted">{{ detailLabel }}</span>
          <span class="muted">{{ detailText.length }} 字符</span>
        </div>
        <pre class="br-detail-body">{{ detailText }}</pre>
      </div>
    </a-drawer>

    <!-- 标注列：新增 / 重命名 -->
    <a-modal v-model:visible="colDialogOpen" :title="colDialogMode === 'add' ? '新增标注列' : '重命名标注列'" :width="360"
      :on-before-ok="submitColumn" ok-text="确定" cancel-text="取消">
      <a-input v-model="colDialogName" placeholder="例如：状态 / 备注 / 标注结果" :max-length="30" allow-clear
        @press-enter="submitColumn" />
      <div class="br-dialog-tip">标注列的内容由你自己填写，不做固定选项；填好后会自动保存到任务上。</div>
    </a-modal>

    <!-- 列设置 -->
    <a-drawer v-model:visible="columnPanelOpen" :width="320" title="显示哪些列" :footer="false">
      <div class="br-col-panel">
        <div class="br-col-actions">
          <a-button size="mini" @click="showAllColumns">全部显示</a-button>
          <a-button size="mini" @click="hideContentColumns">只看输入 / 指标</a-button>
        </div>
        <a-checkbox-group v-model="visibleKeys">
          <a-checkbox v-for="c in allColumns" :key="c.key" :value="c.key">
            <span class="br-col-panel-name">{{ c.label }}</span>
            <span class="muted">（{{ c.width }}px）</span>
          </a-checkbox>
        </a-checkbox-group>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { getToken } from '@/api/client'
import { toast } from '@/utils/feedback'
import { exportRowsToXlsx } from '@/utils/xlsxExport'
import iconToMiddle from '@/imgs/icon/icon_to_middle.svg'
import iconToTop from '@/imgs/icon/icon_to_top.svg'
import iconToBottom from '@/imgs/icon/icon_to_bottom.svg'
import iconToLeft from '@/imgs/icon/icon_to_left.svg'
import iconToRight from '@/imgs/icon/icon_to_right.svg'
import iconToCenter from '@/imgs/icon/icon_to_center.svg'



type AnyRow = string[]

interface AnnCol { id: string; name: string }
interface ColMeta { width: number; wrap: boolean }
interface CondFilter { op: 'contains' | 'notContains' | 'equals' | 'empty' | 'notEmpty'; value: string }

const font_list = [
  "微软雅黑",
  "楷体",
  "宋体",
  "新宋体",
  "黑体",
  "Microsoft YaHei UI",
  "Microsoft JhengHei",
  "JetBrains Mono",
  "Arial",
  "Arial Black",
  "Arial Narrow",
  "Arial Unicode MS",
  "Courier New",
  "Comic Sans MS",
  "Georgia",
  "Impact",
  "Microsoft Sans Serif",
  "Segoe UI",
  "Segoe UI Symbol",
  "Tahoma",
  "Times New Roman",
  "Trebuchet MS",
  "Verdana",
  "Calibri",
  "Cambria",
  "Consolas",
  "等线",
  "华文宋体",
  "华文仿宋",
  "仿宋",
  "华文楷体",
  "Yu Gothic",
  "MS Gothic",
  "MS PGothic",
  "MS UI Gothic",
  "Wingdings",
  "Wingdings 2",
  "Wingdings 3",
]
const ROW_H = 34
const ROW_H_WRAP = 96
const PAGE_SIZE = 300
const MAX_ROWS = 5000

const route = useRoute()
const jobId = String(route.params.jobId || '')

const loading = ref(false)
/** 首次渲染前置为 false：视图与标注都到位后再画表，避免先闪原始表 */
const ready = ref(false)
const truncated = ref(false)
const rows = ref<AnyRow[]>([])
const totalRows = ref(0)
const columns = ref<string[]>([])
const job = reactive<any>({})
const keyword = ref('')
/** 输入框防抖后的关键词（大结果集上避免每次按键都全表扫描） */
const filterKw = ref('')
const onlyFail = ref(false)
const onlyAnnotated = ref(false)

// ---- 标注状态 ----
const annCols = ref<AnnCol[]>([])
/** 行号(1 起) → { colId: 值 } */
const annCells = ref<Record<string, Record<string, string>>>({})
const dirty = ref(false)
const saving = ref(false)
/** 标注读取失败原因（多为后端未重启导致接口不存在） */
const annError = ref('')
let saveTimer: ReturnType<typeof setTimeout> | null = null

// ---- 列配置（宽度 / 自动换行），key = d<索引> | a<标注列 id> ----
const colMeta = reactive<Record<string, ColMeta>>({})
const hiddenColumns = ref<Set<string>>(new Set())
const columnPanelOpen = ref(false)

// ---- 单元格样式（加粗 / 字色 / 底色 / 字体 / 字号），key = `<行号>|<列 key>` ----
type HAlign = 'left' | 'center' | 'right'
type VAlign = 'top' | 'middle' | 'bottom'

interface CellFmt {
  bold?: boolean
  color?: string
  bg?: string
  font?: string
  size?: number
  /** 斜体 / 下划线 / 删除线 */
  italic?: boolean
  underline?: boolean
  strike?: boolean
  /** 水平对齐 */
  halign?: HAlign
  /** 垂直对齐 */
  valign?: VAlign
}
const formats = ref<Record<string, CellFmt>>({})
/** 整表默认字体 / 字号（px），未单独设置的单元格跟随 */
const defaultFont = ref('')
const defaultSize = ref(12)
/** 工具栏下拉的当前值（与默认值分开，选中单元格时只改单元格） */
const fontSel = ref('')
const sizeSel = ref(12)
const fontColor = ref('#1f2329')
const bgColor = ref('#fff1b8')

/** 打开的色板：字体颜色 / 单元格颜色 */
const palette = ref<'' | 'font' | 'bg'>('')

/** 色板 6 行 × 10 列：第一列是灰阶，其余 9 列同色相逐行加深 */
const PALETTE = (() => {
  const hues = ['#3B82F6', '#06B6D4', '#22C55E', '#FACC15', '#F97316', '#EF4444', '#EC4899', '#8B5CF6', '#94A3B8']
  const grays = ['#FFFFFF', '#F2F3F5', '#E5E6EB', '#C9CDD4', '#86909C', '#1D2129']
  const toRgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  const toHex = (rgb: number[]) => '#' + rgb.map((n) => Math.round(Math.max(0, Math.min(255, n))).toString(16).padStart(2, '0')).join('')
  const blend = (hex: string, ratio: number) => {
    // ratio > 0 提亮（混白），ratio < 0 加深（混黑）
    const target = ratio > 0 ? 255 : 0
    const k = Math.abs(ratio)
    return toHex(toRgb(hex).map((n) => n + (target - n) * k))
  }
  const levels = [0, 0.7, 0.45, 0.15, -0.15, -0.35]
  const out: string[] = []
  levels.forEach((lv, i) => {
    out.push(grays[i])
    for (const h of hues) out.push(blend(h, lv).toUpperCase())
  })
  return out
})()

const RECENT_KEY = 'bench.recentColors'

function readRecentColors(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY)
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list.slice(0, 9) : []
  } catch {
    return []
  }
}

const recentColors = ref<string[]>(readRecentColors())

function rememberColor(color: string) {
  const c = color.toUpperCase()
  const list = [c, ...recentColors.value.filter((x) => x.toUpperCase() !== c)].slice(0, 9)
  recentColors.value = list
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(list))
  } catch {
    /* 忽略存储失败 */
  }
}

function togglePalette(which: 'font' | 'bg') {
  palette.value = palette.value === which ? '' : which
}

/** 取色后立即写入选中单元格（未选中时按「选中提示」逻辑，不生效） */
function pickColor(which: 'font' | 'bg', color: string) {
  if (which === 'font') {
    fontColor.value = color
    onPickFontColor(color)
  } else {
    bgColor.value = color
    onPickBgColor(color)
  }
  rememberColor(color)
  palette.value = ''
}

function onMoreColor(which: 'font' | 'bg', ev: Event) {
  const el = ev.target as HTMLInputElement
  if (el?.value) pickColor(which, el.value)
}

// ---- 选区（矩形选择，shift 扩展） ----
interface CellPos { rowNo: number; colKey: string }
const selAnchor = ref<CellPos | null>(null)
const selFocus = ref<CellPos | null>(null)
/** 选中的整列 / 整行（可多选，与单元格矩形互斥） */
const selCols = ref<string[]>([])
const selRows = ref<number[]>([])
/** Shift 扩选时的锚点 */
const colAnchor = ref('')
const rowAnchor = ref(0)
/** 全选（点左上角小三角） */
const selAll = ref(false)

/** 行号栏宽度 */
const GUTTER_W = 46

// ---- 右键菜单 ----
const ctx = reactive({
  open: false,
  x: 0,
  y: 0,
  type: 'col' as 'col' | 'row' | 'cell' | 'all' | 'sel',
  colKey: '',
  rowNo: 0,
})


// ---- 排序与筛选 ----
const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')
/** 按值筛选：列 key → 勾选的值 */
const valueFilters = ref<Record<string, string[]>>({})
/** 按条件筛选：列 key → 条件 */
const condFilters = ref<Record<string, CondFilter>>({})

// ---- 列面板 ----
const panel = reactive({
  open: false, key: '', label: '', annId: null as string | null, x: 0, y: 0, rowCount: 0,
})
const panelTab = ref<'value' | 'cond'>('value')
const valueSearch = ref('')
const draftSel = ref<string[]>([])
const draftAll = ref(true)
const draftCond = ref<CondFilter>({ op: 'contains', value: '' })

// ---- 详情抽屉 / 列对话框 ----
const detailOpen = ref(false)
const detailLabel = ref('')
const detailText = ref('')
const colDialogOpen = ref(false)
const colDialogMode = ref<'add' | 'rename'>('add')
const colDialogName = ref('')
let renameTargetId: string | null = null

const statusText = (s: string) => ({ running: '运行中', done: '已完成', failed: '失败', cancelled: '已取消' }[s] || s)
const statusColor = (s: string) => ({ running: 'blue', done: 'green', failed: 'red', cancelled: 'orange' }[s] || 'gray')

/** 指标列固定宽度；其它列按内容给一个舒服的默认宽度。 */
const METRIC_WIDTH: Record<string, number> = {
  序号: 60,
  状态码: 78,
  是否成功: 84,
  总耗时ms: 96,
  首帧耗时ms: 104,
  响应字节数: 104,
  是否重试: 80,
  错误信息: 220,
  content: 360,
  响应原文: 360,
}
const ANN_WIDTH = 160

function widthFor(name: string): number {
  if (METRIC_WIDTH[name]) return METRIC_WIDTH[name]
  if (/^(content|响应原文)$/.test(name)) return 360
  return 150
}

/** 插入的空白列 / 空白行（只做整体插入，表头留空） */
interface BlankCol { id: number; at: string; side: 'left' | 'right' }
interface BlankRow { id: number; at: number; side: 'up' | 'down' }
/** 被「删除此行」隐藏掉的行号（数据行用原始行号，插入的空白行为负数） */
const hiddenRows = ref<number[]>([])
const blankCols = ref<BlankCol[]>([])
const blankRows = ref<BlankRow[]>([])
/** 插入的空白列表头文字，key = 列 key（`b<序号>`） */
const blankColLabels = ref<Record<string, string>>({})

function blankColLabel(key: string): string {
  return blankColLabels.value[key] ?? ''
}

function onBlankColLabel(key: string, ev: Event) {
  const v = (ev.target as HTMLInputElement).value
  if (v) blankColLabels.value[key] = v
  else delete blankColLabels.value[key]
  scheduleSaveView()
}
let blankColSeq = 1
let blankRowSeq = 1

const BLANK_COL_W = 120

interface RenderColumn {
  key: string
  label: string
  colIdx: number
  annId: string | null
  width: number
  wrap: boolean
  blank?: boolean
}

/** 表头 / 列定义：数据列 + 标注列，宽度与换行取 colMeta 里的用户配置。 */
const allColumns = computed<RenderColumn[]>(() => {
  const data: RenderColumn[] = columns.value.map((name, i) => {
    const key = `d${i}`
    return {
      key,
      label: name,
      colIdx: i,
      annId: null as string | null,
      width: colMeta[key]?.width ?? widthFor(name),
      wrap: colMeta[key]?.wrap ?? false,
    }
  })
  // 「序号」固定排在数据列第一列（key 仍按 CSV 原始下标，取值不受影响）
  const seqIdx = data.findIndex((c) => c.label === '序号')
  if (seqIdx > 0) data.unshift(data.splice(seqIdx, 1)[0])
  const ann: RenderColumn[] = annCols.value.map((c) => {
    const key = `a${c.id}`
    return {
      key,
      label: c.name || '未命名',
      colIdx: -1,
      annId: c.id as string | null,
      width: colMeta[key]?.width ?? ANN_WIDTH,
      wrap: colMeta[key]?.wrap ?? false,
    }
  })
  const list: RenderColumn[] = [...data, ...ann]
  // 空白列按插入锚点放进列序里（锚点列没了就放到最后）
  for (const b of blankCols.value) {
    const key = `b${b.id}`
    const at = list.findIndex((c) => c.key === b.at)
    const pos = at < 0 ? list.length : (b.side === 'left' ? at : at + 1)
    list.splice(pos, 0, {
      key,
      label: blankColLabel(key),
      colIdx: -1,
      annId: null,
      width: colMeta[key]?.width ?? BLANK_COL_W,
      wrap: colMeta[key]?.wrap ?? false,
      blank: true,
    })
  }
  return list
})

const displayColumns = computed(() => allColumns.value.filter((c) => !hiddenColumns.value.has(c.key)))

/** 列设置抽屉用：checkbox-group 双向绑定「显示中的列 key」。 */
const visibleKeys = computed<string[]>({
  get: () => allColumns.value.filter((c) => !hiddenColumns.value.has(c.key)).map((c) => c.key),
  set: (keys) => {
    const next = new Set<string>()
    for (const c of allColumns.value) {
      if (!keys.includes(c.key)) next.add(c.key)
    }
    hiddenColumns.value = next
  },
})

const totalWidth = computed(() => displayColumns.value.reduce((s, c) => s + c.width, 0) || 800)

/** 自动换行时预估的行数（与 .br-cell-text.is-wrap 的 line-clamp 保持一致）。 */
const WRAP_LINES = 4

/** 当前视图用到的最大字号（默认字号与单元格格式里的字号取大），行高随字号一起放大。 */
const maxFontPx = computed(() => {
  let m = defaultSize.value || 12
  for (const f of Object.values(formats.value)) {
    if (f?.size && f.size > m) m = f.size
  }
  return m
})

/** 任一可见列开启自动换行时，行高切到多行模式；字号变大时行高同步放大，避免文字压到相邻行。 */
const rowH = computed(() => {
  const fs = maxFontPx.value
  const line = Math.round(fs * 1.5)
  if (!displayColumns.value.some((c) => c.wrap)) return Math.max(ROW_H, line + 12)
  return Math.max(ROW_H_WRAP, line * WRAP_LINES + 10)
})

// ---- 取值 ----
function valueOf(row: AnyRow, rowNo: number, key: string): string {
  if (key.startsWith('b')) return ''
  if (key.startsWith('a')) {
    return annCells.value[String(rowNo)]?.[key.slice(1)] || ''
  }
  const idx = Number(key.slice(1))
  return row[idx] ?? ''
}

/** 单元格显示值（空白列 / 空白行恒为空） */
function cellText(item: RenderRow | null | undefined, c: RenderColumn): string {
  if (!item) return ''
  const ed = edits.value[editKey(item.rowNo, c.key)]
  if (ed !== undefined) return ed
  if (item.blank || c.blank || c.colIdx < 0) return ''
  return item.row[c.colIdx] ?? ''
}

// ---- 行数据（筛选 + 排序） ----
const successIdx = computed(() => columns.value.findIndex((n) => n === '是否成功'))

interface RenderRow { idx: number; rowNo: number; row: AnyRow; isFail: boolean; hasAnn: boolean; blank?: boolean }

function rowPassesFilters(row: AnyRow, rowNo: number, kw: string): boolean {
  for (const key of Object.keys(valueFilters.value)) {
    const sel = valueFilters.value[key]
    if (!sel || !sel.length) continue
    if (!sel.includes(valueOf(row, rowNo, key))) return false
  }
  for (const key of Object.keys(condFilters.value)) {
    const c = condFilters.value[key]
    const v = valueOf(row, rowNo, key)
    if (c.op === 'contains' && !v.includes(c.value)) return false
    if (c.op === 'notContains' && v.includes(c.value)) return false
    if (c.op === 'equals' && v !== c.value) return false
    if (c.op === 'empty' && v.trim() !== '') return false
    if (c.op === 'notEmpty' && v.trim() === '') return false
  }
  if (kw) {
    const hitRow = row.some((v) => String(v || '').toLowerCase().includes(kw))
    const cellMap = annCells.value[String(rowNo)]
    const hitAnn = !!cellMap && Object.values(cellMap).some((v) => String(v || '').toLowerCase().includes(kw))
    if (!hitRow && !hitAnn) return false
  }
  return true
}

const visibleRows = computed<RenderRow[]>(() => {
  const kw = filterKw.value.trim().toLowerCase()
  const failIdx = successIdx.value
  const out: RenderRow[] = []
  for (let i = 0; i < rows.value.length; i++) {
    const row = rows.value[i]
    const rowNo = i + 1
    if (hiddenRows.value.includes(rowNo)) continue
    const isFail = failIdx >= 0 && row[failIdx] === '失败'
    if (onlyFail.value && !isFail) continue
    const cellMap = annCells.value[String(rowNo)]
    const hasAnn = !!cellMap && Object.values(cellMap).some((v) => String(v || '').trim())
    if (onlyAnnotated.value && !hasAnn) continue
    if (!rowPassesFilters(row, rowNo, kw)) continue
    out.push({ idx: out.length, rowNo, row, isFail, hasAnn })
  }
  // 排序：数字优先按数值，其余按本地化字符串
  const key = sortKey.value
  if (key) {
    const dir = sortDir.value === 'asc' ? 1 : -1
    out.sort((a, b) => {
      const va = valueOf(a.row, a.rowNo, key)
      const vb = valueOf(b.row, b.rowNo, key)
      const na = Number(va)
      const nb = Number(vb)
      if (va !== '' && vb !== '' && !Number.isNaN(na) && !Number.isNaN(nb)) return (na - nb) * dir
      return va.localeCompare(vb, 'zh-CN') * dir
    })
    out.forEach((r, i) => { r.idx = i })
  }
  // 空白行：插在锚点行上/下（锚点不在当前视图里就放头/尾）
  if (blankRows.value.length) {
    for (const b of blankRows.value) {
      const ri = out.findIndex((r) => r.rowNo === b.at)
      const pos = ri < 0 ? (b.side === 'up' ? 0 : out.length) : (b.side === 'up' ? ri : ri + 1)
      out.splice(pos, 0, { idx: 0, rowNo: -b.id, row: [], isFail: false, hasAnn: false, blank: true })
    }
    out.forEach((r, i) => { r.idx = i })
  }
  return out
})

// ---- 单元格选区与样式 ----
function cellFmtKey(rowNo: number, colKey: string): string {
  return `${rowNo}|${colKey}`
}

/** 单元格最终样式：整表默认 + 单元格自身的覆盖 */
function cellCss(rowNo: number, colKey: string): Record<string, string> {
  const f = formats.value[cellFmtKey(rowNo, colKey)]
  const out: Record<string, string> = {}
  if (f?.bold) out.fontWeight = '600'
  if (f?.italic) out.fontStyle = 'italic'
  const deco = [f?.underline ? 'underline' : '', f?.strike ? 'line-through' : ''].filter(Boolean).join(' ')
  if (deco) out.textDecoration = deco
  if (f?.color) out.color = f.color
  if (f?.bg) out.background = f.bg
  const fam = f?.font || defaultFont.value
  if (fam) out.fontFamily = fam
  out.fontSize = `${f?.size || defaultSize.value}px`
  if (f?.halign) {
    out.justifyContent = f.halign === 'left' ? 'flex-start' : f.halign === 'center' ? 'center' : 'flex-end'
    out.textAlign = f.halign
  }
  if (f?.valign) {
    out.alignItems = f.valign === 'top' ? 'flex-start' : f.valign === 'middle' ? 'center' : 'flex-end'
  }
  return out
}

/** 选区内的单元格（按可见行 × 可见列取矩形，上限 4000 格防止误操作卡死） */
const selCells = computed<CellPos[]>(() => {
  const a = selAnchor.value
  const b = selFocus.value
  if (!a || !b) return []
  const cols = displayColumns.value.map((c) => c.key)
  const vr = visibleRows.value
  let ci1 = cols.indexOf(a.colKey)
  let ci2 = cols.indexOf(b.colKey)
  let ri1 = vr.findIndex((r) => r.rowNo === a.rowNo)
  let ri2 = vr.findIndex((r) => r.rowNo === b.rowNo)
  if (ci1 < 0 || ci2 < 0 || ri1 < 0 || ri2 < 0) return []
  if (ri1 > ri2) [ri1, ri2] = [ri2, ri1]
  if (ci1 > ci2) [ci1, ci2] = [ci2, ci1]
  if ((ri2 - ri1 + 1) * (ci2 - ci1 + 1) > 4000) {
    ri2 = Math.min(ri2, ri1 + 3999)
  }
  const out: CellPos[] = []
  for (let r = ri1; r <= ri2; r++) {
    for (let c = ci1; c <= ci2; c++) out.push({ rowNo: vr[r].rowNo, colKey: cols[c] })
  }
  return out
})

/** 列标：A、B…Z、AA、AB… */
function colLetter(index: number): string {
  let n = index + 1
  let s = ''
  while (n > 0) {
    const r = (n - 1) % 26
    s = String.fromCharCode(65 + r) + s
    n = Math.floor((n - 1) / 26)
  }
  return s
}

const nameBoxText = computed(() => {
  if (selAll.value) return '全选'
  const cols = displayColumns.value
  const vr = visibleRows.value
  if (selCols.value.length) {
    const idxs = selCols.value
      .map((k) => cols.findIndex((c) => c.key === k))
      .filter((i) => i >= 0)
      .sort((a, b) => a - b)
    if (!idxs.length) return ''
    const a = colLetter(idxs[0])
    const b = colLetter(idxs[idxs.length - 1])
    if (selRows.value.length) {
      const ris = selRows.value
        .map((no) => vr.findIndex((r) => r.rowNo === no))
        .filter((i) => i >= 0)
        .sort((x, y) => x - y)
      const ra = ris.length ? ris[0] + 1 : 1
      const rb = ris.length ? ris[ris.length - 1] + 1 : vr.length
      return `${a}${ra}:${b}${rb}`
    }
    return idxs.length === 1 ? `${a}列` : `${a}:${b} 列`
  }
  if (selRows.value.length) {
    const ris = selRows.value
      .map((no) => vr.findIndex((r) => r.rowNo === no))
      .filter((i) => i >= 0)
      .sort((x, y) => x - y)
    if (!ris.length) return ''
    const a = ris[0] + 1
    const b = ris[ris.length - 1] + 1
    return ris.length === 1 ? `${a}行` : `${a}:${b} 行`
  }
  const a = selAnchor.value
  if (!a) return ''
  const idx = displayColumns.value.findIndex((c) => c.key === a.colKey)
  return idx >= 0 ? `${colLetter(idx)}${a.rowNo}` : ''
})

/** 工具栏/右键菜单作用的目标单元格：整列 > 整行 > 矩形选区 */
const targetCells = computed<CellPos[]>(() => {
  if (selAll.value) {
    const out: CellPos[] = []
    const cols = displayColumns.value
    for (const r of visibleRows.value) {
      for (const c of cols) {
        if (out.length >= 4000) return out
        out.push({ rowNo: r.rowNo, colKey: c.key })
      }
    }
    return out
  }
  if (selCols.value.length || selRows.value.length) {
    const cols = selCols.value.length
      ? displayColumns.value.filter((c) => selCols.value.includes(c.key))
      : displayColumns.value
    const rowSet = selRows.value.length ? new Set(selRows.value) : null
    const rows = rowSet ? visibleRows.value.filter((r) => rowSet.has(r.rowNo)) : visibleRows.value
    const out: CellPos[] = []
    for (const r of rows) {
      for (const c of cols) {
        if (out.length >= 4000) return out
        out.push({ rowNo: r.rowNo, colKey: c.key })
      }
    }
    return out
  }
  return selCells.value
})

/** 高亮用：整列 / 整行 / 矩形选区都算选中 */
const selSet = computed<Set<string>>(
  () => new Set(targetCells.value.map((p) => cellFmtKey(p.rowNo, p.colKey))),
)

/** 行号 / 列 key 到渲染对象的索引，供状态栏取显示值（含标注、空白列）。 */
const rowByNo = computed(() => new Map(visibleRows.value.map((r) => [r.rowNo, r])))
const colByKey = computed(() => new Map(displayColumns.value.map((c) => [c.key, c])))

/** 数字化：去掉千分位与首尾空白；空或非数字（如带单位的文本）一律按 0 计。 */
function toNumber(text: string): number {
  const t = text.trim().replace(/,/g, '')
  if (!t) return 0
  const n = Number(t)
  return Number.isFinite(n) ? n : 0
}

function fmtNum(n: number): string {
  if (!Number.isFinite(n)) return '0'
  if (Number.isInteger(n)) return String(n)
  return String(Number(n.toFixed(2)))
}

/** 状态栏统计：计数值=选中格数；求和/平均值把非数字单元格按 0 计入。 */
const stat = computed(() => {
  let sum = 0
  for (const p of targetCells.value) {
    const row = rowByNo.value.get(p.rowNo)
    const col = colByKey.value.get(p.colKey)
    const text = col && col.colIdx >= 0 ? cellText(row, col) : ''
    sum += toNumber(text)
  }
  const count = targetCells.value.length
  const avg = count ? sum / count : 0
  return { count, sum, sumText: fmtNum(sum), avgText: fmtNum(avg) }
})

// ---- 单元格原地编辑：双击进入，值存在视图里并持久化 ----
/** 手工改写的单元格文本，key = `<行号>|<列 key>` */
const edits = ref<Record<string, string>>({})
const editing = ref<{ rowNo: number; colKey: string } | null>(null)
const editValue = ref('')

function isEditing(rowNo: number, colKey: string): boolean {
  return !!editing.value && editing.value.rowNo === rowNo && editing.value.colKey === colKey
}

/** 可编辑：数据列、插入的空白列（标注列本身就是输入框，跳过） */
function canEditCell(c: RenderColumn): boolean {
  return !c.annId
}

function editKey(rowNo: number, colKey: string): string {
  return `${rowNo}|${colKey}`
}


function startEdit(item: RenderRow, c: RenderColumn) {
  if (!canEditCell(c)) return
  editing.value = { rowNo: item.rowNo, colKey: c.key }
  editValue.value = edits.value[editKey(item.rowNo, c.key)] ?? cellText(item, c)
  nextTick(() => {
    const el = wrapRef.value?.querySelector<HTMLInputElement>('.br-cell-edit')
    el?.focus()
    el?.select()
  })
}

function commitEdit() {
  const cur = editing.value
  if (!cur) return
  const key = editKey(cur.rowNo, cur.colKey)
  const original = originalText(cur.rowNo, cur.colKey)
  if (editValue.value === original) delete edits.value[key]
  else edits.value[key] = editValue.value
  editing.value = null
  scheduleSaveView()
}

function cancelEdit() {
  editing.value = null
}

/** 原始（未改写）显示值，用于判断是否还原 */
function originalText(rowNo: number, colKey: string): string {
  const row = rowByNo.value.get(rowNo)
  const col = colByKey.value.get(colKey)
  return col && col.colIdx >= 0 && row ? (row.row[col.colIdx] ?? '') : ''
}

interface SelRect { left: number; top: number; width: number; height: number }

/** 选区外框位置（body 坐标系，含左侧行号栏宽度） */
const selRect = computed<SelRect | null>(() => {
  const cols = displayColumns.value
  const vr = visibleRows.value
  if (!cols.length || !vr.length) return null

  const columnsRange = (c1: number, c2: number) => {
    let left = GUTTER_W
    for (let i = 0; i < c1; i++) left += cols[i].width
    let width = 0
    for (let i = c1; i <= c2; i++) width += cols[i].width
    return { left, width }
  }

  const h = rowH.value

  if (selAll.value) {
    return { left: GUTTER_W, top: 0, width: totalWidth.value, height: vr.length * h }
  }

  if (selCols.value.length || selRows.value.length) {
    let ci1 = 0
    let ci2 = cols.length - 1
    if (selCols.value.length) {
      const idxs = selCols.value
        .map((k) => cols.findIndex((c) => c.key === k))
        .filter((i) => i >= 0)
        .sort((a, b) => a - b)
      if (!idxs.length) return null
      ci1 = idxs[0]
      ci2 = idxs[idxs.length - 1]
    }
    let ri1 = 0
    let ri2 = vr.length - 1
    if (selRows.value.length) {
      const rowSet = new Set(selRows.value)
      const firstIdx = vr.findIndex((r) => rowSet.has(r.rowNo))
      const lastIdx = vr.length - 1 - [...vr].reverse().findIndex((r) => rowSet.has(r.rowNo))
      if (firstIdx < 0) return null
      ri1 = firstIdx
      ri2 = lastIdx
    }
    const { left, width } = columnsRange(ci1, ci2)
    return { left, width, top: ri1 * h, height: (ri2 - ri1 + 1) * h }
  }

  const a = selAnchor.value
  const b = selFocus.value
  if (!a || !b) return null
  let ci1 = cols.findIndex((c) => c.key === a.colKey)
  let ci2 = cols.findIndex((c) => c.key === b.colKey)
  let ri1 = vr.findIndex((r) => r.rowNo === a.rowNo)
  let ri2 = vr.findIndex((r) => r.rowNo === b.rowNo)
  if (ci1 < 0 || ci2 < 0 || ri1 < 0 || ri2 < 0) return null
  if (ci1 > ci2) [ci1, ci2] = [ci2, ci1]
  if (ri1 > ri2) [ri1, ri2] = [ri2, ri1]
  const { left, width } = columnsRange(ci1, ci2)
  return { left, width, top: ri1 * h, height: (ri2 - ri1 + 1) * h }
})

function onColClick(c: { key: string }, ev?: MouseEvent) {
  window.getSelection()?.removeAllRanges()
  selAll.value = false
  selRows.value = []
  selAnchor.value = null
  selFocus.value = null
  const keys = displayColumns.value.map((x) => x.key)
  const cur = keys.indexOf(c.key)
  // Shift + 点击：从锚点列扩选到当前列（多列）
  if (ev?.shiftKey && colAnchor.value) {
    const from = keys.indexOf(colAnchor.value)
    if (from >= 0 && cur >= 0) {
      const [a, b] = from <= cur ? [from, cur] : [cur, from]
      selCols.value = keys.slice(a, b + 1)
      return
    }
  }
  if (selCols.value.length === 1 && selCols.value[0] === c.key) {
    selCols.value = []
    colAnchor.value = ''
  } else {
    selCols.value = [c.key]
    colAnchor.value = c.key
  }
}

function onRowClick(item: RenderRow, ev?: MouseEvent) {
  window.getSelection()?.removeAllRanges()
  selAll.value = false
  selCols.value = []
  selAnchor.value = null
  selFocus.value = null
  const nos = visibleRows.value.map((r) => r.rowNo)
  const cur = nos.indexOf(item.rowNo)
  // Shift + 点击：从锚点行扩选到当前行（多行）
  if (ev?.shiftKey && rowAnchor.value) {
    const from = nos.indexOf(rowAnchor.value)
    if (from >= 0 && cur >= 0) {
      const [a, b] = from <= cur ? [from, cur] : [cur, from]
      selRows.value = nos.slice(a, b + 1)
      return
    }
  }
  if (selRows.value.length === 1 && selRows.value[0] === item.rowNo) {
    selRows.value = []
    rowAnchor.value = 0
  } else {
    selRows.value = [item.rowNo]
    rowAnchor.value = item.rowNo
  }
}

function onCellClick(item: RenderRow, colKey: string, ev: MouseEvent) {
  // 清掉浏览器原生文字选区，否则 Shift 扩选会把文字颜色成块
  window.getSelection()?.removeAllRanges()
  const pos: CellPos = { rowNo: item.rowNo, colKey }
  if (ev.shiftKey && selAnchor.value) {
    selFocus.value = pos
  } else {
    selAnchor.value = pos
    selFocus.value = pos
  }
  selCols.value = []
  selRows.value = []
  selAll.value = false
}

function clearSelection() {
  selAnchor.value = null
  selFocus.value = null
  selCols.value = []
  selRows.value = []
  colAnchor.value = ''
  rowAnchor.value = 0
  selAll.value = false
}

/** 左上角小三角：全选整张表（再点一次取消） */
function selectAllCells() {
  selAll.value = !selAll.value
  selCols.value = []
  selRows.value = []
  colAnchor.value = ''
  rowAnchor.value = 0
  selAnchor.value = null
  selFocus.value = null
}

/** 单元格是否处于选中态（全选时全部算选中） */
function isInSel(rowNo: number, colKey: string): boolean {
  return selAll.value || selSet.value.has(cellFmtKey(rowNo, colKey))
}

/** Esc 取消选区 */
/** Ctrl/⌘ + S：不走浏览器“保存网页”，把视图 + 标注立即写回后端。 */
async function saveToServer() {
  if (savingNow.value) return
  savingNow.value = true
  try {
    if (editing.value) commitEdit()
    if (viewTimer) {
      clearTimeout(viewTimer)
      viewTimer = null
    }
    const viewOk = await saveView()
    const annOk = await flushSave()
    if (viewOk && annOk) toast.success('已保存')
    else if (viewOk || annOk) toast.warning('部分保存失败')
    else toast.error('保存失败')
  } finally {
    savingNow.value = false
  }
}

function onKeydown(ev: KeyboardEvent) {
  if ((ev.ctrlKey || ev.metaKey) && !ev.altKey && (ev.key === 's' || ev.key === 'S')) {
    ev.preventDefault()
    ev.stopPropagation()
    void saveToServer()
    return
  }
  if (ev.key !== 'Escape') return
  if (ctx.open) {
    ctx.open = false
    return
  }
  if (targetCells.value.length) clearSelection()
}

// ---- 右键菜单 ----
function onCellCtx(ev: MouseEvent, col: any, item: RenderRow) {
  const t = ev.target as HTMLElement | null
  // 标注输入框保留浏览器原生右键菜单（剪切/粘贴）
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return
  ev.preventDefault()
  ev.stopPropagation()
  openCtx(ev, 'cell', col, item)
}

function openCtx(ev: MouseEvent, type: 'col' | 'row' | 'cell' | 'all' | 'sel', col?: any, item?: RenderRow) {
  // 全选状态下右键任意位置，都直接给「整表」菜单
  if (selAll.value) type = 'all'

  // 右键落点已经在多选区域内 → 给「多选」菜单，保留原选区
  if (type === 'cell' && col && item && isInSel(item.rowNo, col.key)
    && (selCols.value.length || selRows.value.length || selCells.value.length > 1)) {
    type = 'sel'
  }
  if (type === 'col' && col && selCols.value.includes(col.key) && selCols.value.length > 1) {
    type = 'sel'
  }
  if (type === 'row' && item && selRows.value.includes(item.rowNo) && selRows.value.length > 1) {
    type = 'sel'
  }

  const menuW = 200
  const menuH = type === 'col' ? 300 : type === 'sel' ? 160 : 170
  ctx.type = type
  // 统一菜单都基于「目标列」：右键点中的列 > 已选列 > 当前第一列
  ctx.colKey = col?.key || selCols.value[0] || displayColumns.value[0]?.key || ''
  ctx.rowNo = item?.rowNo || 0
  ctx.x = Math.min(ev.clientX, window.innerWidth - menuW - 8)
  ctx.y = Math.min(ev.clientY, window.innerHeight - menuH - 8)
  ctx.open = true

  if (type === 'sel' || type === 'all') return

  selAll.value = false
  // 右键同时把目标选中，保证「复制/清除格式」作用对象一目了然
  if (type === 'col' && col) {
    selCols.value = [col.key]
    colAnchor.value = col.key
    selRows.value = []
    selAnchor.value = null
    selFocus.value = null
  } else if (type === 'row' && item) {
    selRows.value = [item.rowNo]
    rowAnchor.value = item.rowNo
    selCols.value = []
  } else if (type === 'cell' && col && item) {
    selAnchor.value = { rowNo: item.rowNo, colKey: col.key }
    selFocus.value = selAnchor.value
    selCols.value = []
    selRows.value = []
  }
}

function ctxColumn() {
  return displayColumns.value.find((c) => c.key === ctx.colKey)
}

/** TSV 字段转义：含制表符/换行/引号时加引号并转义内部引号 */
function tsvCell(v: string): string {
  return /[\t\n\r"]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v
}

function htmlCell(v: string): string {
  const esc = v
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
  // mso-data-placement:same-cell 明确告诉 Excel：这是单元格内换行，不要拆成多行
  return esc.replace(/\r?\n/g, '<br style="mso-data-placement:same-cell">')
}

/**
 * 复制成表格：同时写 text/html + text/plain。
 * Excel / WPS 粘贴 text/html 时会识别成单元格，单元格内的换行也会保留在同一格里。
 */
async function copyTable(rows: string[][]): Promise<void> {
  const tsv = rows.map((r) => r.map(tsvCell).join('\t')).join('\n')
  const html = `<table>${rows.map((r) => `<tr>${r.map((c) => `<td>${htmlCell(c)}</td>`).join('')}</tr>`).join('')}</table>`
  try {
    if (navigator.clipboard?.write && typeof ClipboardItem !== 'undefined') {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/plain': new Blob([tsv], { type: 'text/plain' }),
          'text/html': new Blob([html], { type: 'text/html' }),
        }),
      ])
      toast.success('已复制到剪贴板')
      return
    }
  } catch { /* 回退到纯文本 */ }
  await copyText(tsv)
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('已复制到剪贴板')
  } catch {
    toast.error('复制失败（浏览器未授权剪贴板）')
  }
}

function ctxCopyColumn() {
  const cols = displayColumns.value.filter((c) => ctxKeys.value.includes(c.key))
  ctx.open = false
  if (!cols.length) return
  const matrix = visibleRows.value.map((r) =>
    cols.map((c) => (c.annId ? cellValue(r.rowNo, c.annId) : cellText(r, c))),
  )
  void copyTable(matrix)
}




function ctxSort(dir: 'asc' | 'desc') {
  if (!ctx.colKey) return
  sortKey.value = ctx.colKey
  sortDir.value = dir
  ctx.open = false
  resetScroll()
}

function ctxFilter() {
  const c = ctxColumn()
  ctx.open = false
  if (!c) return
  openColumnPanel(c, null)
}

/** 统一菜单作用的目标列：多选列时全部生效 */
const ctxKeys = computed<string[]>(() => {
  if (selCols.value.length > 1) return selCols.value
  return ctx.colKey ? [ctx.colKey] : []
})

const selColWrap = computed(() => !!colMeta[ctxKeys.value[0] || '']?.wrap)

function ctxWrap() {
  const keys = ctxKeys.value
  if (!keys.length) return
  const on = !colMeta[keys[0]]?.wrap
  for (const key of keys) {
    const meta = colMeta[key] || (colMeta[key] = { width: widthFor(colLabel(key)), wrap: false })
    meta.wrap = on
  }
  ctx.open = false
  nextTick(() => { measure() })
}

/** 列宽自适应：按该列可见内容最长字符估算（中文按 2 个字符宽） */
function ctxFitWidth() {
  const keys = ctxKeys.value
  ctx.open = false
  if (!keys.length) return
  for (const key of keys) {
    const c = displayColumns.value.find((x) => x.key === key)
    if (!c) continue
    let max = c.label.length * 2
    for (const r of visibleRows.value.slice(0, 2000)) {
      const v = c.annId ? cellValue(r.rowNo, c.annId) : cellText(r, c)
      for (const line of String(v).split('\n')) {
        let w = 0
        for (const ch of line) w += ch.charCodeAt(0) > 255 ? 2 : 1
        if (w > max) max = w
      }
    }
    const width = Math.max(80, Math.min(900, Math.round(max * 7 + 24)))
    colMeta[key] = { width, wrap: colMeta[key]?.wrap ?? false }
  }
  nextTick(() => { measure() })
}

/** 列 key → 列名（新建 colMeta 时给个合适默认宽度） */
function colLabel(key: string): string {
  return displayColumns.value.find((c) => c.key === key)?.label || ''
}

/** 插入空白行：整行插入，表头/单元格留空，不做单元格错位 */
function ctxInsertRow(side: 'up' | 'down') {
  ctx.open = false
  const vr = visibleRows.value
  // 锚点：右键所在行 > 当前选中行 > 首行/末行
  const at = ctx.rowNo > 0
    ? ctx.rowNo
    : (selRows.value[0] || (side === 'up' ? vr[0]?.rowNo : vr[vr.length - 1]?.rowNo) || 0)
  if (!at) return
  blankRows.value = [...blankRows.value, { id: blankRowSeq++, at, side }]
  scheduleSaveView()
}

/** 删除行：数据行从视图隐藏，插入的空白行直接移除 */
function ctxDeleteRow() {
  ctx.open = false
  const vrs = visibleRows.value
  const anchors = (ctx.rowNo !== 0
    ? [ctx.rowNo]
    : (selRows.value.length ? selRows.value : (vrs[0] ? [vrs[0].rowNo] : [])))
  if (!anchors.length) return
  const blankIds = anchors.filter((n) => n < 0).map((n) => -n)
  const dataNos = anchors.filter((n) => n > 0)
  if (blankIds.length) blankRows.value = blankRows.value.filter((b) => !blankIds.includes(b.id))
  if (dataNos.length) {
    const set = new Set([...hiddenRows.value, ...dataNos])
    hiddenRows.value = [...set]
  }
  selRows.value = []
  ctx.rowNo = 0
  scheduleSaveView()
}

/** 插入空白列：整列插入，表头留空 */
function ctxInsertCol(side: 'left' | 'right') {
  ctx.open = false
  const at = ctxKeys.value[0] || displayColumns.value[0]?.key || ''
  if (!at) return
  blankCols.value = [...blankCols.value, { id: blankColSeq++, at, side }]
  scheduleSaveView()
  nextTick(() => { measure() })
}

function ctxHideColumn() {
  const keys = ctxKeys.value
  if (!keys.length) return
  const set = new Set(hiddenColumns.value)
  for (const k of keys) set.add(k)
  hiddenColumns.value = set
  ctx.open = false
}

function ctxDeleteColumn() {
  const keys = ctxKeys.value
  ctx.open = false
  // 空白列是本次插入的，直接移除
  const blanks = keys.filter((k) => k.startsWith('b'))
  if (blanks.length) {
    const ids = blanks.map((k) => Number(k.slice(1)))
    blankCols.value = blankCols.value.filter((b) => !ids.includes(b.id))
    for (const k of blanks) delete colMeta[k]
    scheduleSaveView()
    nextTick(() => { measure() })
  }
  const cols = displayColumns.value.filter((c) => keys.includes(c.key))
  if (!cols.length) return
  // 标注列真删，数据列仅从当前视图隐藏
  const annIds = cols.filter((c) => c.annId).map((c) => c.annId as string)
  if (annIds.length) {
    annCols.value = annCols.value.filter((c) => !annIds.includes(c.id))
    for (const rowNo of Object.keys(annCells.value)) {
      const map = annCells.value[rowNo]
      for (const id of annIds) delete map[id]
      if (!Object.keys(map).length) delete annCells.value[rowNo]
    }
    for (const c of cols) delete colMeta[c.key]
    scheduleSave()
    void flushSave()
  }
  const rest = cols.filter((c) => !c.annId).map((c) => c.key)
  if (rest.length) {
    const set = new Set(hiddenColumns.value)
    for (const k of rest) set.add(k)
    hiddenColumns.value = set
  }
  for (const c of cols) {
    delete valueFilters.value[c.key]
    delete condFilters.value[c.key]
  }
  selCols.value = []
  resetScroll()
}

function ctxClearFormat() {
  ctx.open = false
  const cells = targetCells.value.length
    ? targetCells.value
    : (ctxKeys.value.length && ctx.rowNo
      ? ctxKeys.value.map((k) => ({ rowNo: ctx.rowNo, colKey: k }))
      : [])
  clearFormat(cells)
}












function applyFormat(patch: CellFmt, onlyIf?: (cur: CellFmt) => boolean) {
  if (!targetCells.value.length) return
  const map: Record<string, CellFmt> = { ...formats.value }
  for (const p of targetCells.value) {
    const k = cellFmtKey(p.rowNo, p.colKey)
    const cur: CellFmt = { ...(map[k] || {}) }
    if (onlyIf && !onlyIf(cur)) continue
    for (const [field, value] of Object.entries(patch)) {
      const key = field as keyof CellFmt
      if (value === undefined || value === null || value === '') delete cur[key]
      else (cur as any)[key] = value
    }
    if (Object.keys(cur).length) map[k] = cur
    else delete map[k]
  }
  formats.value = map
}

type TextStyleField = 'bold' | 'italic' | 'underline' | 'strike'

/** 选区是否全部应用了该字形（用于按钮高亮） */
function allHaveStyle(field: TextStyleField): boolean {
  return targetCells.value.length > 0
    && targetCells.value.every((p) => !!formats.value[cellFmtKey(p.rowNo, p.colKey)]?.[field])
}

/** 加粗 / 斜体 / 下划线 / 删除线：已全部应用时再点一次取消 */
function toggleStyle(field: TextStyleField) {
  if (!targetCells.value.length) return
  applyFormat({ [field]: allHaveStyle(field) ? undefined : true } as CellFmt)
}

const selHasBold = computed(() => allHaveStyle('bold'))
const selHasItalic = computed(() => allHaveStyle('italic'))
const selHasUnderline = computed(() => allHaveStyle('underline'))
const selHasStrike = computed(() => allHaveStyle('strike'))

function onPickFontColor(color: string) {
  applyFormat({ color: color || undefined })
}

function onPickBgColor(color: string) {
  applyFormat({ bg: color || undefined })
}

/** 有选区时作用于选中单元格，没有选区时调整为整表默认 */
function onPickFont(value: any) {
  const name = typeof value === 'string' ? value : ''
  fontSel.value = name
  if (targetCells.value.length) applyFormat({ font: name || undefined })
  else defaultFont.value = name
}

function onPickSize(value: any) {
  const n = Number(value)
  if (!n) return
  sizeSel.value = n
  if (targetCells.value.length) applyFormat({ size: n })
  else defaultSize.value = n
}

/** 当前选区第一个单元格的对齐状态（用于按钮高亮） */
const selHalign = computed<HAlign | undefined>(() => {
  const p = targetCells.value[0]
  return p ? formats.value[cellFmtKey(p.rowNo, p.colKey)]?.halign : undefined
})

const selValign = computed<VAlign | undefined>(() => {
  const p = targetCells.value[0]
  return p ? formats.value[cellFmtKey(p.rowNo, p.colKey)]?.valign : undefined
})

/** 对齐：选区已全部是该对齐方式时再点一次取消 */
function setAlign(kind: 'halign' | 'valign', value: HAlign | VAlign) {
  if (!targetCells.value.length) return
  const same = targetCells.value.every(
    (p) => formats.value[cellFmtKey(p.rowNo, p.colKey)]?.[kind] === value,
  )
  applyFormat(kind === 'halign'
    ? { halign: (same ? undefined : value) as HAlign | undefined }
    : { valign: (same ? undefined : value) as VAlign | undefined })
}



function clearFormat(cells?: CellPos[]) {
  const list = cells || targetCells.value
  if (!list.length) return
  const map: Record<string, CellFmt> = { ...formats.value }
  for (const p of list) delete map[cellFmtKey(p.rowNo, p.colKey)]
  formats.value = map
}


// ---- 虚拟滚动 ----
const wrapRef = ref<HTMLElement | null>(null)
const scrollTop = ref(0)

const viewportH = ref(600)
const overscan = 8

const windowRows = computed(() => {
  const h = rowH.value
  const start = Math.max(0, Math.floor(scrollTop.value / h) - overscan)
  const end = Math.min(visibleRows.value.length, Math.ceil((scrollTop.value + viewportH.value) / h) + overscan)
  return visibleRows.value.slice(start, end)
})

function onScroll() {
  const el = wrapRef.value
  if (el) scrollTop.value = el.scrollTop
}

function measure() {
  if (wrapRef.value) viewportH.value = wrapRef.value.clientHeight
}

// ---- 数据加载 ----
async function apiGet<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      detail = ((await res.json()) as any).detail || detail
    } catch { /* ignore */ }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

async function reload() {
  loading.value = true
  ready.value = false
  truncated.value = false
  rows.value = []
  try {
    // 先把「调整」拿到手（视图 + 标注），再读行数据，避免先渲染原表再套用调整造成闪现
    await Promise.all([loadView(), loadAnnotations()])
    // 取第一页拿到表头与任务信息
    const first = await apiGet<any>(`/api/bench/jobs/${jobId}/rows?offset=0&limit=${PAGE_SIZE}`)
    Object.assign(job, first.job || {})
    columns.value = first.columns || []
    const total = first.total || 0
    totalRows.value = total
    const cap = Math.min(total, MAX_ROWS)
    truncated.value = total > MAX_ROWS
    rows.value = first.rows || []
    // 剩余行分批补齐（虚拟滚动下渲染量恒定，加载期间表格已可交互）
    while (rows.value.length < cap) {
      const page = await apiGet<any>(
        `/api/bench/jobs/${jobId}/rows?offset=${rows.value.length}&limit=${PAGE_SIZE}`,
      )
      const got: AnyRow[] = page.rows || []
      if (!got.length) break
      rows.value = rows.value.concat(got)
    }
    ready.value = true
    await nextTick()
    measure()
  } catch (err: any) {
    ready.value = true
    toast.error(err.message || '加载结果失败')
  } finally {
    loading.value = false
  }
}

async function loadAnnotations() {
  try {
    const data = await apiGet<{ cols: AnnCol[]; cells: Record<string, Record<string, string>> }>(
      `/api/bench/jobs/${jobId}/annotations`,
    )
    annCols.value = (data.cols || []).filter((c) => c && c.id)
    annCells.value = data.cells || {}
    dirty.value = false
    annError.value = ''
  } catch (err: any) {
    // 后端未重启（接口 404）时最容易出现：显式提示，避免以为标注丢了
    annError.value = err.message || '未知错误'
    toast.error(`标注加载失败：${annError.value}`)
  }
}

// ---- 标注保存（防抖整体提交） ----
function scheduleSave() {
  dirty.value = true
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => { void flushSave() }, 400)
}

/** 离开输入框立即落库，避免刚填完就刷新丢数据。 */
function onCellBlur() {
  void flushSave()
}

async function flushSave(): Promise<boolean> {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (!dirty.value) return true
  saving.value = true
  try {
    const res = await fetch(`/api/bench/jobs/${jobId}/annotations`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ cols: annCols.value, cells: annCells.value }),
    })
    if (!res.ok) {
      throw new Error(res.status === 404
        ? '保存标注失败：接口不存在，请重启后端后再试'
        : `保存标注失败（${res.status}）`)
    }
    dirty.value = false
    return true
  } catch (err: any) {
    toast.error(err.message || '保存标注失败')
    return false
  } finally {
    saving.value = false
  }
}

function cellValue(rowNo: number, colId: string | null): string {
  if (!colId) return ''
  return annCells.value[String(rowNo)]?.[colId] || ''
}

function onCellInputEvent(rowNo: number, colId: string | null, e: Event) {
  if (!colId) return
  onCellInput(rowNo, colId, (e.target as HTMLInputElement).value)
}

function onCellInput(rowNo: number, colId: string, value: string) {
  const key = String(rowNo)
  const map = annCells.value[key] || (annCells.value[key] = {})
  if (value) map[colId] = value
  else delete map[colId]
  if (!Object.keys(map).length) delete annCells.value[key]
  scheduleSave()
}

// ---- 列宽拖拽 ----
let resizing: { key: string; startX: number; startW: number } | null = null

function startResize(e: MouseEvent, key: string, width: number) {
  e.preventDefault()
  e.stopPropagation()
  resizing = { key, startX: e.clientX, startW: width }
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
}

function onResizeMove(e: MouseEvent) {
  if (!resizing) return
  const next = Math.max(60, Math.min(900, resizing.startW + (e.clientX - resizing.startX)))
  const meta = colMeta[resizing.key] || (colMeta[resizing.key] = { width: next, wrap: false })
  meta.width = next
}

function stopResize() {
  resizing = null
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
}

// ---- 列面板：打开 / 排序 / 换行 / 删除列 ----
function openColumnPanel(col: { key: string; label: string; annId: string | null }, e: MouseEvent | null) {
  // 再次点击同一列：收起面板
  if (panel.open && panel.key === col.key) {
    panel.open = false
    return
  }
  const rect = e ? (e.currentTarget as HTMLElement).getBoundingClientRect() : null
  panel.key = col.key
  panel.label = col.label
  panel.annId = col.annId
  panel.x = Math.min(rect ? rect.left : ctx.x, window.innerWidth - 340)
  panel.y = Math.min(rect ? rect.bottom + 4 : ctx.y, window.innerHeight - 540)
  panel.rowCount = rows.value.length
  panelTab.value = 'value'
  valueSearch.value = ''
  panel.open = true // 先打开，panelValues 才会按该列算值
  // 草稿：沿用已有筛选，否则默认全选
  const existing = valueFilters.value[col.key]
  draftSel.value = existing ? [...existing] : panelValues.value.map((v) => v.value)
  draftAll.value = !existing
  draftCond.value = { ...(condFilters.value[col.key] || { op: 'contains', value: '' }) }
}

/** 面板里该列的全部去重值与出现次数（最多 300 个，超出时提示）。 */
const panelValueData = computed<{ values: { value: string; count: number }[]; overflow: boolean }>(() => {
  if (!panel.open) return { values: [], overflow: false }
  const key = panel.key
  const map = new Map<string, number>()
  for (let i = 0; i < rows.value.length; i++) {
    const v = valueOf(rows.value[i], i + 1, key)
    map.set(v, (map.get(v) || 0) + 1)
  }
  const arr = [...map.entries()].map(([value, count]) => ({ value, count }))
  arr.sort((a, b) => b.count - a.count || a.value.localeCompare(b.value, 'zh-CN'))
  return { values: arr.slice(0, 300), overflow: arr.length > 300 }
})

const panelValues = computed(() => panelValueData.value.values)
const panelOverflow = computed(() => panelValueData.value.overflow)

/** 值列表再叠一层关键词过滤。 */
const visibleValues = computed(() => {
  const kws = valueSearch.value.trim().toLowerCase().split(/\s+/).filter(Boolean)
  if (!kws.length) return panelValues.value
  return panelValues.value.filter((v) => kws.every((kw) => v.value.toLowerCase().includes(kw)))
})

const panelWrap = computed(() => colMeta[panel.key]?.wrap ?? false)

function onDraftAllChange(v: unknown) {
  toggleDraftAll(!!v)
}

function onWrapChange(v: unknown) {
  setWrap(!!v)
}

/** 标注列重命名：先收起面板，再打开对话框。 */
function renamePanelColumn() {
  const id = panel.annId
  if (!id) return
  const col = annCols.value.find((c) => c.id === id)
  panel.open = false
  if (!col) return
  colDialogMode.value = 'rename'
  renameTargetId = id
  colDialogName.value = col.name
  colDialogOpen.value = true
}

function toggleDraftAll(checked: boolean) {
  draftAll.value = checked
  draftSel.value = checked ? panelValues.value.map((v) => v.value) : []
}

function toggleDraftValue(value: string) {
  const set = new Set(draftSel.value)
  if (set.has(value)) set.delete(value)
  else set.add(value)
  draftSel.value = [...set]
  draftAll.value = draftSel.value.length === panelValues.value.length
}

function applySort(dir: 'asc' | 'desc') {
  sortKey.value = panel.key
  sortDir.value = dir
  panel.open = false
  resetScroll()
}

function setWrap(v: boolean) {
  const meta = colMeta[panel.key] || (colMeta[panel.key] = { width: 150, wrap: false })
  meta.wrap = v
  nextTick(() => { measure() })
}

function hasFilter(key: string): boolean {
  const sel = valueFilters.value[key]
  const cond = condFilters.value[key]
  return (!!sel && sel.length > 0) || !!cond
}

const activeFilterCount = computed(() =>
  Object.keys(valueFilters.value).filter((k) => valueFilters.value[k]?.length).length
  + Object.keys(condFilters.value).length,
)

function clearPanelFilter() {
  const key = panel.key
  delete valueFilters.value[key]
  delete condFilters.value[key]
  draftSel.value = panelValues.value.map((v) => v.value)
  draftAll.value = true
  draftCond.value = { op: 'contains', value: '' }
  panel.open = false
  resetScroll()
}

function confirmPanel() {
  const key = panel.key
  if (panelTab.value === 'value') {
    const all = panelValues.value.map((v) => v.value)
    if (draftSel.value.length === 0 || draftSel.value.length >= all.length) delete valueFilters.value[key]
    else valueFilters.value[key] = [...draftSel.value]
    // 按值筛选与按条件筛选互斥，避免叠加后结果为空
    delete condFilters.value[key]
  } else {
    const c = draftCond.value
    const needsValue = c.op !== 'empty' && c.op !== 'notEmpty'
    if (needsValue && !c.value.trim()) {
      toast.warning('请输入筛选内容')
      return
    }
    condFilters.value[key] = { op: c.op, value: c.value }
    delete valueFilters.value[key]
  }
  panel.open = false
  resetScroll()
}

function clearAllFilters() {
  valueFilters.value = {}
  condFilters.value = {}
  resetScroll()
}

function removePanelColumn() {
  const { key, annId } = panel
  if (annId) {
    // 标注列：连同已填内容一起删除
    annCols.value = annCols.value.filter((c) => c.id !== annId)
    for (const rowNo of Object.keys(annCells.value)) {
      const map = annCells.value[rowNo]
      delete map[annId]
      if (!Object.keys(map).length) delete annCells.value[rowNo]
    }
    delete colMeta[key]
    scheduleSave()
    void flushSave()
  } else {
    // 数据列：只从当前视图隐藏，原始 CSV 与下载不受影响
    const set = new Set(hiddenColumns.value)
    set.add(key)
    hiddenColumns.value = set
  }
  delete valueFilters.value[key]
  delete condFilters.value[key]
  panel.open = false
  resetScroll()
}

// ---- 标注列管理 ----
function openAddCol() {
  colDialogMode.value = 'add'
  renameTargetId = null
  colDialogName.value = ''
  colDialogOpen.value = true
}

function submitColumn(): boolean {
  const name = colDialogName.value.trim()
  if (!name) {
    toast.error('列名不能为空')
    return false
  }
  if (colDialogMode.value === 'add') {
    const id = `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`
    annCols.value.push({ id, name })
  } else if (renameTargetId) {
    const col = annCols.value.find((c) => c.id === renameTargetId)
    if (col) col.name = name
  }
  scheduleSave()
  void flushSave()
  colDialogOpen.value = false
  return true
}

// ---- 列显隐 ----
function showAllColumns() {
  hiddenColumns.value = new Set()
}

/** 只看输入列与固定指标列（隐藏自定义列 / content 等长文本列）。 */
function hideContentColumns() {
  const hidden = new Set<string>()
  const metrics = new Set(Object.keys(METRIC_WIDTH))
  columns.value.forEach((name, i) => {
    if (!metrics.has(name)) hidden.add(`d${i}`)
  })
  hiddenColumns.value = hidden
}

// ---- 单元格详情 ----
function openDetail(label: string, text: string) {
  detailLabel.value = label
  detailText.value = text || ''
  detailOpen.value = true
}

// ---- 下载 / 关闭 ----
/** 任务时间戳：yyyy-mm-dd-hhmmss（优先用任务创建时间）。 */
function jobStamp(): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  const raw = String(job.created_at || '').replace(' ', 'T')
  let d = raw ? new Date(raw) : new Date()
  if (Number.isNaN(d.getTime())) d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
}

/** 下载文件名：测试集名_测试结果_yyyy-mm-dd-hhmmss */
function resultFileBase(withAnnot?: boolean): string {
  const set = String(job.dataset_name || job.name || jobId).replace(/[\\/:*?"<>|]/g, '_')
  const tag = withAnnot ? '测试结果_标注' : '测试结果'
  return `${set}_${tag}_${jobStamp()}`
}

/** 原始结果 CSV（服务端原样，不含标注与视图调整）。 */
async function downloadRawCsv() {
  try {
    const res = await fetch(`/api/bench/jobs/${jobId}/csv`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) throw new Error('下载失败')
    const blob = await res.blob()
    const u = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = u
    a.download = `${resultFileBase()}.csv`
    a.click()
    URL.revokeObjectURL(u)
  } catch (err: any) {
    toast.error(err.message || '下载失败')
  }
}

/** 导出上限：避免在浏览器里拼超大表把内存打满。 */
const EXPORT_MAX_ROWS = 20000
const NUMERIC_LABELS = new Set(['序号', '状态码', '总耗时ms', '首帧耗时ms', '响应字节数'])

/** 导出前把还没加载完的行补齐（结果页默认只加载前 5000 行）。 */
async function ensureRowsForExport(): Promise<boolean> {
  const target = Math.min(totalRows.value || rows.value.length, EXPORT_MAX_ROWS)
  if (rows.value.length >= target) return totalRows.value <= EXPORT_MAX_ROWS
  loading.value = true
  try {
    while (rows.value.length < target) {
      const page = await apiGet<any>(
        `/api/bench/jobs/${jobId}/rows?offset=${rows.value.length}&limit=${PAGE_SIZE}`,
      )
      const got: AnyRow[] = page.rows || []
      if (!got.length) break
      rows.value = rows.value.concat(got)
    }
  } catch (err: any) {
    toast.error(err.message || '补齐结果行失败')
  } finally {
    loading.value = false
  }
  await nextTick()
  return totalRows.value <= EXPORT_MAX_ROWS
}

/** 按当前视图（隐藏列 / 列宽 / 换行 / 排序 / 筛选 / 标注）导出 xlsx。 */
async function exportView() {
  try {
    const complete = await ensureRowsForExport()
    if (!complete) {
      toast.warning(`结果超过 ${EXPORT_MAX_ROWS} 行，只导出前 ${EXPORT_MAX_ROWS} 行`)
    }
    const cols = displayColumns.value
    if (!cols.length) {
      toast.warning('没有可导出的列，请先在列设置里恢复列')
      return
    }
    const data = visibleRows.value.map((item) =>
      cols.map((c) => (c.annId ? cellValue(item.rowNo, c.annId) : cellText(item, c))),
    )
    const visible = visibleRows.value
    await exportRowsToXlsx({
      sheetName: '结果',
      columns: cols.map((c) => ({
        label: c.label,
        width: c.width,
        wrap: c.wrap,
        numeric: !c.annId && NUMERIC_LABELS.has(c.label),
      })),
      rows: data,
      defaultFont: defaultFont.value || undefined,
      defaultSize: defaultSize.value,
      cellStyle: (r, c) => {
        const item = visible[r]
        const col = cols[c]
        if (!item || !col) return null
        const f = formats.value[cellFmtKey(item.rowNo, col.key)]
        if (!f) return null
        return {
          bold: f.bold,
          italic: f.italic,
          underline: f.underline,
          strike: f.strike,
          color: f.color,
          bg: f.bg,
          font: f.font,
          fontSize: f.size,
          halign: f.halign,
          valign: f.valign,
        }
      },
      fileName: resultFileBase(),
    })
  } catch (err: any) {
    toast.error(err.message || '导出失败')
  }
}

// ---- 视图设置持久化：后端为准（按任务存），localStorage 只做离线兜底缓存 ----
const VIEW_KEY = `bench.view.${jobId}`
let viewTimer: ReturnType<typeof setTimeout> | null = null
/** Ctrl+S 保存中，防止连按重复提交 */
const savingNow = ref(false)

interface ViewPayload {
  colMeta?: Record<string, { width: number; wrap: boolean }>
  hidden?: string[]
  sort?: { key: string; dir: 'asc' | 'desc' } | null
  valueFilters?: Record<string, string[]>
  condFilters?: Record<string, CondFilter>
  /** 单元格样式，key = `<行号>|<列 key>` */
  formats?: Record<string, CellFmt>
  defaultFont?: string
  defaultSize?: number
  /** 插入的空白列 / 空白行 */
  blankCols?: BlankCol[]
  blankRows?: BlankRow[]
  /** 被删除（隐藏）的行号 */
  hiddenRows?: number[]
  /** 插入空白列的表头文字 */
  blankColLabels?: Record<string, string>
  /** 手工改写的单元格文本，key = `<行号>|<列 key>` */
  edits?: Record<string, string>
}

function currentView(): ViewPayload {
  return {
    colMeta: JSON.parse(JSON.stringify(colMeta)),
    hidden: [...hiddenColumns.value],
    sort: sortKey.value ? { key: sortKey.value, dir: sortDir.value } : null,
    valueFilters: JSON.parse(JSON.stringify(valueFilters.value)),
    condFilters: JSON.parse(JSON.stringify(condFilters.value)),
    formats: JSON.parse(JSON.stringify(formats.value)),
    defaultFont: defaultFont.value,
    defaultSize: defaultSize.value,
    blankCols: JSON.parse(JSON.stringify(blankCols.value)),
    blankRows: JSON.parse(JSON.stringify(blankRows.value)),
    hiddenRows: [...hiddenRows.value],
    blankColLabels: JSON.parse(JSON.stringify(blankColLabels.value)),
    edits: JSON.parse(JSON.stringify(edits.value)),
  }
}

function applyView(data: ViewPayload | null | undefined) {
  if (!data) return
  if (data.colMeta && typeof data.colMeta === 'object') {
    for (const [k, v] of Object.entries(data.colMeta)) {
      if (v && typeof v.width === 'number') colMeta[k] = { width: v.width, wrap: !!v.wrap }
    }
  }
  if (Array.isArray(data.hidden)) hiddenColumns.value = new Set<string>(data.hidden)
  if (data.sort?.key) {
    sortKey.value = data.sort.key
    sortDir.value = data.sort.dir === 'desc' ? 'desc' : 'asc'
  }
  if (data.valueFilters && typeof data.valueFilters === 'object') valueFilters.value = data.valueFilters
  if (data.condFilters && typeof data.condFilters === 'object') condFilters.value = data.condFilters
  if (data.formats && typeof data.formats === 'object') formats.value = { ...data.formats }
  if (typeof data.defaultFont === 'string') {
    defaultFont.value = data.defaultFont
    fontSel.value = data.defaultFont
  }
  if (typeof data.defaultSize === 'number' && data.defaultSize > 0) {
    defaultSize.value = data.defaultSize
    sizeSel.value = data.defaultSize
  }
  if (Array.isArray(data.blankCols)) {
    const list: BlankCol[] = []
    for (const b of data.blankCols) {
      if (!b || typeof b.id !== 'number' || typeof b.at !== 'string') continue
      list.push({ id: b.id, at: b.at, side: b.side === 'left' ? 'left' : 'right' })
    }
    blankCols.value = list
    blankColSeq = list.reduce((m, b) => Math.max(m, b.id), 0) + 1
  }
  if (Array.isArray(data.blankRows)) {
    const list: BlankRow[] = []
    for (const b of data.blankRows) {
      if (!b || typeof b.id !== 'number' || typeof b.at !== 'number') continue
      list.push({ id: b.id, at: b.at, side: b.side === 'up' ? 'up' : 'down' })
    }
    blankRows.value = list
    blankRowSeq = list.reduce((m, b) => Math.max(m, b.id), 0) + 1
  }
  if (Array.isArray(data.hiddenRows)) {
    hiddenRows.value = data.hiddenRows.filter((n) => typeof n === 'number')
  }
  if (data.blankColLabels && typeof data.blankColLabels === 'object') {
    blankColLabels.value = { ...data.blankColLabels }
  }
  if (data.edits && typeof data.edits === 'object') {
    edits.value = { ...data.edits }
  }
}

function readLocalView(): ViewPayload | null {
  try {
    const raw = localStorage.getItem(VIEW_KEY)
    return raw ? (JSON.parse(raw) as ViewPayload) : null
  } catch {
    return null
  }
}

function writeLocalView(data: ViewPayload) {
  try {
    localStorage.setItem(VIEW_KEY, JSON.stringify(data))
  } catch { /* 忽略 */ }
}

/** 保存视图到后端；失败时至少保住本地缓存，下次打开还能恢复。 */
async function saveView(): Promise<boolean> {
  const payload = currentView()
  writeLocalView(payload)
  try {
    const res = await fetch(`/api/bench/jobs/${jobId}/view`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`${res.status}`)
    return true
  } catch {
    // 后端不可用时不打扰用户，本地缓存已写入
    return false
  }
}

function scheduleSaveView() {
  if (viewTimer) clearTimeout(viewTimer)
  viewTimer = setTimeout(() => { void saveView() }, 400)
}

/**
 * 载入视图：优先后端；后端没有（老任务 / 未重启服务）时退回本地缓存，
 * 并把本地这份同步写回后端，保证下一次打开就是后端数据。
 */
async function loadView() {
  try {
    const data = await apiGet<ViewPayload>(`/api/bench/jobs/${jobId}/view`)
    if (data && Object.keys(data).length) {
      applyView(data)
      writeLocalView(data)
      return
    }
    const local = readLocalView()
    if (local) {
      applyView(local)
      void saveView()
    }
  } catch {
    applyView(readLocalView())
  }
}


/** 刷新 / 关页前把还没提交的标注用 keepalive 请求补发一次。 */
function onBeforeUnload() {
  if (!dirty.value) return
  try {
    const body = JSON.stringify({ cols: annCols.value, cells: annCells.value })
    if (body.length > 60000) return // 超出 keepalive 限制，交给下一页重新编辑
    void fetch(`/api/bench/jobs/${jobId}/annotations`, {
      method: 'PUT',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body,
    })
  } catch { /* 页面即将卸载，忽略 */ }
}

function closeWindow() {
  window.close()
}

function resetScroll() {
  scrollTop.value = 0
  if (wrapRef.value) wrapRef.value.scrollTop = 0
}

function onResize() {
  measure()
  if (panel.open) panel.open = false
}

/** 点击面板与表头之外的地方关闭面板（表头自身负责切换/收起）。 */
function onDocMousedown(e: MouseEvent) {
  const target = e.target as HTMLElement | null
  if (ctx.open && !target?.closest('.br-ctx')) ctx.open = false
  if (palette.value && !target?.closest('.br-fmt-dd')) palette.value = ''
  if (!panel.open) return
  if (target?.closest('.br-panel') || target?.closest('.br-th')) return
  panel.open = false
}

onMounted(() => {
  void reload()
  window.addEventListener('resize', onResize)
  document.addEventListener('mousedown', onDocMousedown)
  window.addEventListener('beforeunload', onBeforeUnload)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  document.removeEventListener('mousedown', onDocMousedown)
  window.removeEventListener('beforeunload', onBeforeUnload)
  window.removeEventListener('keydown', onKeydown)
  stopResize()
  if (saveTimer) clearTimeout(saveTimer)
  if (kwTimer) clearTimeout(kwTimer)
  if (viewTimer) {
    clearTimeout(viewTimer)
    saveView()
  }
  if (dirty.value) void flushSave()
})

watch([filterKw, onlyFail, onlyAnnotated], resetScroll)

let kwTimer: ReturnType<typeof setTimeout> | null = null
watch(keyword, (v) => {
  if (kwTimer) clearTimeout(kwTimer)
  kwTimer = setTimeout(() => { filterKw.value = v }, 200)
})

// 换行 / 列宽变化后重算可视区
watch(rowH, () => { nextTick(measure) })

// 视图调整（列宽 / 换行 / 隐藏列 / 排序 / 筛选）自动落本地，刷新后恢复
watch([colMeta, hiddenColumns, valueFilters, condFilters, sortKey, sortDir, formats, defaultFont, defaultSize], scheduleSaveView, { deep: true })
</script>

<style lang="less" scoped>
.bench-result {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-fill-1);
}

/* 底部状态栏：右侧显示选区统计，仿 WPS */
.br-statusbar {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 18px;
  height: 26px;
  padding: 16px 32px;
  border-top: 1px solid var(--color-border-2);
  background: var(--color-fill-2);
  font-size: 12px;
  color: var(--color-text-2);
  user-select: none;

  b {
    font-weight: 500;
    color: var(--color-text-1);
    font-variant-numeric: tabular-nums;
  }
}

.br-st-hint {
  color: var(--color-text-3);
  font-size: 11px;
}

.br-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  background: var(--color-bg-2);
  border-bottom: 1px solid var(--color-border-2);
}

.br-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.br-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-1);
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.br-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-2);
}

.br-meta .ok {
  color: rgb(var(--green-6));
}

.br-meta .err {
  color: rgb(var(--red-6));
}

.muted {
  color: var(--color-text-3);
}

.br-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.br-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--color-bg-2);
  border-bottom: 1px solid var(--color-border-2);
  font-size: 12px;
}

.br-count {
  color: var(--color-text-3);
  margin-left: auto;
}

.br-saving {
  color: rgb(var(--orange-6));
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.br-warn {
  color: rgb(var(--red-6));
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: default;
}

.br-grid-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: var(--color-bg-2);
}

.br-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 180px;
  color: var(--color-text-3);
  font-size: 12px;
}

.br-loading .spin {
  animation: br-spin 1s linear infinite;
}

@keyframes br-spin {
  to {
    transform: rotate(360deg);
  }
}

.br-sheet {
  position: relative;
  min-width: 100%;
}

/* 列标 + 列名两层表头，整体吸顶 */
.br-colhead {
  position: sticky;
  top: 0;
  z-index: 6;
  display: flex;
  background: var(--color-bg-1);
  border-bottom: 1px solid var(--color-border-2);
}

.br-corner {
  position: sticky;
  left: 0;
  z-index: 8;
  flex: 0 0 auto;
  width: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-left: 8px;
  font-size: 11px;
  color: var(--color-text-2);
  background: var(--color-fill-2);
  border-right: 1px solid var(--color-border-2);
  overflow: hidden;
  white-space: nowrap;
  cursor: pointer;
  user-select: none;

  /* 左上角小三角（全选按钮） */
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    width: 0;
    height: 0;
    border-top: 7px solid rgb(var(--primary-6));
    border-right: 7px solid transparent;
  }

  &:hover {
    background: var(--color-fill-3);
  }

  &.is-on {
    background: rgba(var(--primary-2), 0.9);
    color: rgb(var(--primary-6));
  }
}

.br-head-main {
  flex: 1 1 auto;
}

.br-let-row {
  display: flex;
  height: 22px;
  background: var(--color-fill-2);
  border-bottom: 1px solid var(--color-border-1);
}

.br-let {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--color-text-3);
  border-right: 1px solid var(--color-border-1);
  overflow: hidden;
  cursor: pointer;
  user-select: none;

  &:hover {
    background: var(--color-fill-3);
  }

  &.is-on {
    background: rgba(var(--primary-2), 0.9);
    color: rgb(var(--primary-6));
  }
}

.br-head-row {
  display: flex;
  background: var(--color-fill-2);
  height: 34px;
}

.br-th {
  position: relative;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-1);
  border-right: 1px solid var(--color-border-2);
  overflow: hidden;
  cursor: pointer;
  user-select: none;

  &:hover {
    background: var(--color-fill-3);
  }

  &.is-sorted {
    background: rgba(var(--primary-1), 0.6);
  }

  &.is-on {
    background: rgba(var(--primary-2), 0.9);
  }
}

.br-th-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.br-th-flag {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--color-text-3);

  &.is-active {
    color: rgb(var(--primary-6));
  }
}

/* 列宽拖拽手柄 */
.br-resize {
  position: absolute;
  top: 0;
  right: -2px;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 1;

  &::after {
    content: '';
    display: block;
    width: 1px;
    height: 100%;
    margin-left: 2px;
    background: transparent;
  }

  &:hover::after {
    background: rgb(var(--primary-6));
  }
}

.br-body {
  position: relative;
}

.br-row {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  background: var(--color-bg-2);

  &.fail {
    background: rgba(var(--red-1), 0.5);
  }

  &.has-ann {
    box-shadow: inset 2px 0 0 rgb(var(--green-5));
  }

  &:hover {
    background: var(--color-fill-1);
  }
}

.br-td {
  position: relative;
  box-sizing: border-box;
  user-select: none;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 8px;
  font-size: 12px;
  color: var(--color-text-1);
  border-right: 1px solid var(--color-border-1);
  border-bottom: 1px solid var(--color-border-1);
  overflow: hidden;
}

/* 选区内部：去掉单元格边线（宽度置 0，外宽不变，不会挤出空白），只留整体外框 */
.br-td.in-sel {
  border-right-width: 0;
  border-bottom-width: 0;
}

.br-selbox {
  position: absolute;
  box-sizing: border-box;
  z-index: 3;
  border: 2px solid rgb(var(--primary-6));
  pointer-events: none;
  box-shadow: 0 0 0 1px rgba(var(--primary-6), 0.15);
}

.br-td-ann {
  background: rgba(var(--green-1), 0.35);
}

/* 选中单元格：淡蓝底 + 内描边 */

.br-gutter {
  position: sticky;
  left: 0;
  z-index: 4;
  flex: 0 0 auto;
  width: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--color-text-3);
  background: var(--color-fill-2);
  border-right: 1px solid var(--color-border-2);
  border-bottom: 1px solid var(--color-border-1);
  user-select: none;
  cursor: pointer;

  &:hover {
    background: var(--color-fill-3);
  }

  &.is-on {
    background: rgba(var(--primary-2), 0.9);
    color: rgb(var(--primary-6));
    font-weight: 600;
  }
}

.br-row.is-on {
  background: rgba(var(--primary-1), 0.35);
}

/* 右键菜单 */
.br-ctx {
  position: fixed;
  z-index: 1000;
  min-width: 168px;
  padding: 4px 0;
  background: var(--color-bg-popup);
  border: 1px solid var(--color-border-2);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.br-ctx-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 32px;
  padding: 0 12px;
  font-size: 12px;
  color: var(--color-text-1);
  cursor: pointer;
  user-select: none;

  &:hover {
    background: var(--color-fill-2);
  }

  &.danger {
    color: rgb(var(--danger-6));
  }
}

.br-ctx-icon {
  font-size: 12px;
  color: var(--color-text-3);
}

.br-ctx-sub {
  font-size: 12px;
  color: var(--color-text-3);
}

.br-ctx-sep {
  height: 1px;
  margin: 4px 0;
  background: var(--color-border-1);
}

.br-td.in-sel::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(var(--primary-6), 0.14);
  pointer-events: none;
}

.br-fmtbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 10px;
  border-bottom: 1px solid var(--color-border-1);
  background: var(--color-bg-1);
}

/* 左侧清除格式：文字在上、图标在下 */
.br-fmt-tall {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: 62px;
  height: 54px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--color-text-2);
  font-size: 16px;
  cursor: pointer;
  transition: background 0.15s;

  .br-tall-text {
    font-size: 11px;
    line-height: 1;
    color: var(--color-text-3);
  }

  &:hover {
    background: var(--color-fill-2);
  }
}

/* 中间两行：上排字体/字号，下排字形与颜色 */
.br-fmt-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.br-fmt-row {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 26px;
}

.br-fg-font {
  width: 122px;
}

.br-fg-size {
  width: 62px;
}

.br-fmt-ic {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--color-text-1);
  font-size: 15px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: var(--color-fill-2);
  }

  &.is-on {
    background: rgba(var(--primary-6), 0.12);
    color: rgb(var(--primary-6));
  }
}

/* 字体/单元格颜色按钮：底部一条当前颜色 */
.br-fmt-color {
  flex-direction: column;
  justify-content: flex-start;
  padding-top: 3px;

  .br-color-bar {
    position: absolute;
    left: 4px;
    right: 4px;
    bottom: 3px;
    height: 3px;
    border-radius: 1px;
  }
}

.br-fmt-dd {
  position: relative;
}

/* 对齐按钮：3 列 × 2 行（上排垂直对齐，下排水平对齐） */
.br-align-grid {
  display: grid;
  grid-template-columns: repeat(3, 26px);
  grid-template-rows: 26px 26px;
  gap: 2px 2px;
  align-items: center;
}

/* 垂直对齐小图标：三条横线靠上/居中/靠下 */
.br-va {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 14px;
  height: 16px;

  i {
    display: block;
    height: 2px;
    border-radius: 1px;
    background: currentColor;
  }

  &.is-top {
    justify-content: flex-start;
  }

  &.is-middle {
    justify-content: center;
  }

  &.is-bottom {
    justify-content: flex-end;
  }
}

.br-fmt-sep {
  width: 1px;
  height: 20px;
  margin: 0 4px;
  background: var(--color-border-2);
}

.br-palette {
  position: absolute;
  top: 32px;
  left: 0;
  z-index: 60;
  width: 248px;
  padding: 8px;
  border: 1px solid var(--color-border-2);
  border-radius: 6px;
  background: var(--color-bg-1);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

.br-pal-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 4px;
}

.br-pal-sw {
  width: 100%;
  aspect-ratio: 1 / 1;
  padding: 0;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 3px;
  cursor: pointer;

  &.is-cur {
    outline: 2px solid rgb(var(--primary-6));
    outline-offset: 1px;
  }
}

.br-pal-title {
  margin: 8px 0 4px;
  font-size: 12px;
  color: var(--color-text-3);
}

.br-pal-recent {
  grid-auto-rows: 20px;
}

.br-pal-empty {
  grid-column: 1 / -1;
  font-size: 12px;
  color: var(--color-text-4);
}

.br-pal-more {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding-top: 7px;
  border-top: 1px solid var(--color-border-1);
  font-size: 12px;
  color: var(--color-text-2);
  cursor: pointer;

  input[type='color'] {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
  }
}

.br-pal-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: conic-gradient(#ef4444, #facc15, #22c55e, #06b6d4, #3b82f6, #8b5cf6, #ef4444);
}

.br-fmt-hint {
  font-size: 12px;
  color: var(--color-text-2);

  &.muted {
    color: var(--color-text-3);
  }
}

/* 插入列的列表头输入框（选中列名即可改名） */
.br-th-edit {
  flex: 1;
  min-width: 0;
  width: 100%;
  height: 100%;
  padding: 0;
  border: none;
  background: transparent;
  font-size: 12px;
  font-family: inherit;
  color: var(--color-text-1);
  outline: none;

  &:hover {
    border-color: var(--color-border-2);
    background: var(--color-bg-2);
  }

  &:focus {
    border-color: rgb(var(--primary-6));
    background: var(--color-bg-2);
  }

  &::placeholder {
    color: var(--color-text-3);
  }
}

/* 单元格原地编辑输入框 */
.br-cell-edit {
  flex: 1;
  min-width: 0;
  width: 100%;
  height: 100%;
  padding: 0;
  border: none;
  border-radius: 3px;
  background: var(--color-bg-2);
  font-size: inherit;
  font-family: inherit;
  color: var(--color-text-1);
  outline: none;
}

.br-cell-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 自动换行：多行截断，点眼睛看全文 */
.br-cell-text.is-wrap {
  white-space: normal;
  word-break: break-all;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.br-zoom {
  flex-shrink: 0;
  color: var(--color-text-3);

  &:hover {
    color: rgb(var(--primary-6));
  }
}

.br-ann-input {
  user-select: text;
  width: 100%;
  height: 26px;
  padding: 0 6px;
  font-family: inherit;
  font-size: inherit;
  color: inherit;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 3px;
  outline: none;

  &:hover {
    border-color: var(--color-border-2);
    background: var(--color-bg-2);
  }

  &:focus {
    border-color: rgb(var(--primary-5));
    background: var(--color-bg-2);
  }
}

.br-empty {
  padding: 60px 0;
}

/* ---- 列面板 ---- */
.br-panel {
  position: fixed;
  z-index: 1000;
  width: 320px;
  max-height: 520px;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-2);
  border: 1px solid var(--color-border-2);
  border-radius: 6px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  font-size: 12px;
  overflow: hidden;
}

.br-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px 6px;
}

.br-panel-col {
  font-weight: 600;
  color: var(--color-text-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.br-sort-row {
  display: flex;
  gap: 8px;
  padding: 0 12px 8px;
}

.br-sort-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 28px;
  font-size: 12px;
  color: var(--color-text-1);
  background: var(--color-fill-1);
  border: 1px solid var(--color-border-2);
  border-radius: 4px;
  cursor: pointer;

  &:hover {
    border-color: rgb(var(--primary-5));
    color: rgb(var(--primary-6));
  }

  &.on {
    border-color: rgb(var(--primary-6));
    color: rgb(var(--primary-6));
    background: rgba(var(--primary-1), 0.5);
  }
}

.br-panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px 8px;
  border-bottom: 1px solid var(--color-border-2);
}

.br-wrap-label {
  color: var(--color-text-2);
}

.br-panel-tabs {
  display: flex;
  gap: 16px;
  padding: 8px 12px 0;
}

.br-tab {
  padding-bottom: 6px;
  color: var(--color-text-2);
  cursor: pointer;
  border-bottom: 2px solid transparent;

  &.on {
    color: rgb(var(--primary-6));
    border-bottom-color: rgb(var(--primary-6));
  }
}

.br-panel-search {
  padding: 8px 12px 4px;
}

.br-value-list {
  flex: 1;
  min-height: 120px;
  max-height: 240px;
  overflow: auto;
  padding: 4px 12px;
}

.br-value-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  height: 30px;

  :deep(.arco-checkbox) {
    display: flex;
    align-items: center;
    min-width: 0;
  }
}

.br-value-text {
  display: inline-block;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.br-value-tip {
  padding: 6px 0;
}

.br-cond {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  min-height: 76px;
}

.br-panel-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid var(--color-border-2);
  background: var(--color-fill-1);
}

.br-panel-spacer {
  flex: 1;
}

.br-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.br-detail-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border-2);
}

.br-detail-body {
  flex: 1;
  margin: 8px 0 0;
  padding: 10px;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--color-fill-1);
  border-radius: 4px;
  overflow: auto;
}

.br-dialog-tip {
  margin-top: 10px;
  font-size: 12px;
  color: var(--color-text-3);
  line-height: 1.6;
}

.br-col-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.br-col-actions {
  display: flex;
  gap: 8px;
}

.br-col-panel-name {
  font-size: 12px;
}
</style>
