## 新增需求

### 需求:自动历史记录
系统必须将发送过的请求自动保存到历史记录中（localStorage）。

#### 场景:请求发送后自动保存
- **当** 用户发送一个 HTTP 或 WebSocket 请求
- **那么** 请求信息（URL、Method、Headers、Body、Body Type、Auth 设置、时间戳）自动追加到历史记录

#### 场景:历史记录上限
- **当** 历史记录超过 50 条
- **那么** 自动删除最旧的记录，只保留最近 50 条

#### 场景:历史记录快速重放
- **当** 用户点击历史记录中的某条
- **那么** 创建一个新 Tab，用该条的请求信息预填充请求构造器
- **当** 构造器预填充完成
- **那么** 用户只需点击 Send 即可重放请求

#### 场景:清空历史记录
- **当** 用户点击"清空历史"按钮
- **那么** 所有历史记录被删除，空出 localStorage 空间

### 需求:可保存 Collection
系统必须支持将请求保存到命名 Collection 中，实现分组管理。

#### 场景:创建 Collection
- **当** 用户在侧边栏点击"新建 Collection"
- **那么** 系统提示输入 Collection 名称，创建空 Collection

#### 场景:保存请求到 Collection
- **当** 用户在请求构造器中点击"保存到 Collection"
- **那么** 系统显示 Collection 选择器，允许选择已有 Collection 或新建
- **当** 用户选择/创建 Collection 并确认
- **那么** 当前请求被保存到该 Collection 中

#### 场景:从 Collection 打开请求
- **当** 用户点击 Collection 中的某个请求
- **那么** 创建一个新 Tab，用该请求的信息预填充请求构造器

#### 场景:重命名 / 删除 Collection 中的请求
- **当** 用户右键点击 Collection 中的某个请求
- **那么** 显示重命名和删除选项
- **当** 用户确认删除
- **那么** 该请求从 Collection 中移除

#### 场景:重命名 / 删除 Collection
- **当** 用户右键点击 Collection 名称
- **那么** 显示重命名和删除选项
- **当** 用户确认删除 Collection
- **那么** 整个 Collection（包含其中所有请求）被删除

### 需求:localStorage 持久化
历史记录和 Collection 必须持久化在浏览器 localStorage 中。

#### 场景:页面刷新后数据保留
- **当** 用户刷新页面
- **那么** 历史记录和 Collection 完整保留，侧边栏自动恢复显示

#### 场景:容量限制
- **当** localStorage 用量接近 5MB 上限
- **那么** 系统提示用户清理历史记录或删除 Collection
