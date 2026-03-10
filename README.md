# Furigana Assistant

这是一个用于日文文本的振假名标注的开源项目, 帮助用户快速实现日文文本的振假名注音需求. 


## 目录

- [Furigana Assistant](#furigana-assistant)
	- [目录](#目录)
	- [安装方法](#安装方法)
	- [软件界面](#软件界面)
	- [标准结构](#标准结构)
	- [字典](#字典)
	- [输入](#输入)
	- [词语添加](#词语添加)
	- [转义字符](#转义字符)
	- [方向键导航](#方向键导航)
	- [推荐分割方式](#推荐分割方式)
	- [待完成任务](#待完成任务)
  

## 安装方法

访问[Github Release](https://github.com/OneThree132639/FuriganaAssistant/releases/tag/v1.0.7)
 - `Windows`用户请下载`FuriganaAssistant.exe`文件, 下载之后可以直接运行. 
 - `MacOS`用户请下载`FuriganaAssistant.dmg`文件, 打开文件之后拖动其中的`FuriganaAssistant.app`到`应用程序(Application)`文件夹, 即可作为应用程序使用. 


## 软件界面

运行程序之后, 可以看到视图上方的4个按钮, 对应本软件的4个功能界面, 点击按钮即可跳转至对应页面. 

1. `Dictionary Viewer`字典页面: 左侧是字典列表, 可以查看当前保存词语, 词语按照[标准结构](#标准结构)进行保存. 右侧是词语添加组件. 
2. `Input Text`文本输入页面: 在此处输入需要添加振假名的文本. 
3. `Output Text`文本输出页面: 左侧是处理后的文本, 按照[输出形式3](#output3)以普通文本形式显示. 已被注音的文本以及注音用`蓝色`进行标注, 检测到的未被注音的`汉字`、`阿拉伯数字`以及`英文字母`会被标注为红色. 右侧为词语添加组件. 
4. `Font Manager`字体管理页面: 在此处选择输出为`.docx`文件时, 文本的字体、字号、列数. 剩余部分为输出效果展示(暂未实现). 


## 标准结构

本软件支持4种振假名标注方式: 
1. <span id="output0"></span>输出形式0: 振假名按照词语划分方式标注在单个字符或多个字符正上方, 大小为文本字号大小的一半. 输出为`.docx`文件. 可以通过菜单栏`File -> Save As Docx (Type 0)`或快捷键`Ctrl + 0`或`⌘‌Cmd + 0`输出.
2. <span id="output1"></span>输出形式1: 振假名按照词语划分方式标注在字符右侧, 大小为文本字号的一半, 可以排列两行. 输出为`.docx`文件. 可以通过菜单栏`File -> Save As Docx (Type 1)`或快捷键`Ctrl + 1`或`⌘‌Cmd + 1`输出. 
3. <span id="output2"></span>输出形式2: 振假名按照词语划分在词语右侧利用小括号`()`进行标注. 输出为`.docx`文件. 可以通过菜单栏`File -> Save As Docx (Type 2)`或快捷键`Ctrl + 2`或`⌘‌Cmd + 2`输出. 
4. <span id="output3"></span>输出形式3: 振假名按照词语划分在词语右侧利用小括号`()`进行标注. 输出为`.txt`文件. 可以通过菜单栏`File -> Save As Text`或快捷键`Ctrl + S`或`⌘‌Cmd + S`输出. 

为了实现上述多种输出方式, 保存于字典中的词语需要保存多种信息. 包括`Japanese`, `Kana`, `Division0`, `Division1`, `Type`, `Priority`6项.  

具体描述如下: 
1. `Japanese`, `Kana`: 包含须注音的词语以及其对应的振假名. 
2. `Division0`, `Division1`: 词语的划分方式, 区分汉字和假名. 其中`Division0`适用于[输出形式0](#output0), `Division1`适用于剩余3种输出形式. 
3. `Type`: 词语的词性, 包括`名詞`, `五段`, `上下`, `形容`, `英語`, `固有`, `サ変`, `カ変`. 
4. `Priority`: 词语的优先级. 

划分方式说明如下: 
1. 除了`固有`和`英語`词性之外, 其余词语的`Japanese`和`Kana`要求不可以出现除`汉字`、`假名`和`阿拉伯数字`以及划分字符`/`, `\`, `*`之外的字符且划分必须完全区分汉字与假名; `英語`不可以出现除了英文字母之外的字符. 
2. `Division0`包含数字`-1`, `0`, `1`, `2`以及划分字符`/`, `*`, 其中`-1`表示不添加注音, `0`表示居中注音, `1`表示`0-1-0`形式注音, `2`表示`1-2-1`形式注音. 应用于[输出形式0](#output0). 
3. `Division1`包含数字`-1`, `0`以及划分字符`\`, `*`, 其中`-1`表示不添加注音, `0`表示注音. 对于[输出形式1](#output1), 如果存在`连续2个0`分割, 这两个分割分别作为注音的上下两行, 否则只注音在上一行. 对于[输出形式2](#output2)和[输出形式3](#output3), 将连续的`0`分割合并. 
4. `Japanese`和`Kana`的使用`/`, `\`, `*`与`Division0`、`Division1`对应进行划分. 
5. `*`划分字符用于划分词干与词尾. 

下表为各个词性词语划分的说明和示例: 
| 词性(`Type`) | 说明 | `Japanese` | `Kana` | `Division0` | `Division1` | [输出形式0](#output0) | [输出形式1](#output1) | [输出形式2](#output2) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `名詞` | 包含所有`名詞`, `副詞`, `形容動詞`(`第二类形容词`)等本身不存在活用变形的词语 | `本` | `ほん` | `0` | `0` | ![`docx0_hon`](./resources/pictures/docx0_hon.png) | ![`docx1_hon`](./resources/pictures/docx1_hon.png) | ![`docx2_hon`](./resources/pictures/docx2_hon.png) |
|  |  | `別/\に` | `べつ/\に` | `0/-1` | `0\-1` | ![`docx0_betsuni`](./resources/pictures/docx0_betsuni.png) | ![`docx1_betsuni`](./resources/pictures/docx1_betsuni.png) | ![`docx2_betsuni`](./resources/pictures/docx2_betsuni.png) |
|  |  | `嗚呼` | `ああ` | `2` | `0` | ![`docx0_aa`](./resources/pictures/docx0_aa.png) | ![`docx1_aa`](./resources/pictures/docx1_aa.png) | ![`docx2_aa`](./resources/pictures/docx2_aa.png) |
|  |  | `正/真/\正/銘` | `しょう/しん/\しょう/めい` | `0/0/0/0` | `0\0` | ![`docx0_shoushinshoumei`](./resources/pictures/docx0_shoushinshoumei.png) | ![`docx1_shoushinshoumei`](./resources/pictures/docx1_shoushinshoumei.png) | ![`docx2_shoushinshoumei`](./resources/pictures/docx2_shoushinshoumei.png) |
| `五段` | 部分词尾为`う`, `く`, `ぐ`, `す`, `つ`, `ぬ`, `ぶ`, `む`, `る`其中之一的词语, 对应`五段动词`或`第一类动词` | `書*く` | `か*く` | `0*-1` | `0*-1` | ![`docx0_kaku`](./resources/pictures/docx0_kaku.png) | ![`docx1_kaku`](./resources/pictures/docx1_kaku.png) | ![`docx2_kaku`](./resources/pictures/docx2_kaku.png) |
|  |  | `絡/\ま*る` | `から/\ま*る` | `0/-1*-1` | `0\-1*-1` | ![`docx0_karamaru`](./resources/pictures/docx0_karamaru.png) | ![`docx1_karamaru`](./resources/pictures/docx1_karamaru.png) | ![`docx2_karamaru`](./resources/pictures/docx2_karamaru.png) |
|  |  | `躊躇*う` | `ためら*う` | `1*-1` | `0*-1` | ![`docx0_tamerau`](./resources/pictures/docx0_tamerau.png) | ![`docx1_tamerau`](./resources/pictures/docx1_tamerau.png) | ![`docx2_tamerau`](./resources/pictures/docx2_tamerau.png) |
| `上下` | 部分词尾为`る`且其之前一个假名属于`い段`或`え段`其中之一的词语, 对应`上一段动词`, `下一段动词`或`第二类动词` | `生/\き*る` | `い/\き*る` | `0/0*-1` | `0\0*-1` | ![`docx0_ikiru`](./resources/pictures/docx0_ikiru.png) | ![`docx1_ikiru`](./resources/pictures/docx1_ikiru.png) | ![`docx2_ikiru`](./resources/pictures/docx2_ikiru.png) |
|  |  | `出*る` | `で*る` | `0*-1` | `0*-1` | ![`docx0_deru`](./resources/pictures/docx0_deru.png) | ![`docx1_deru`](./resources/pictures/docx1_deru.png) | ![`docx2_deru`](./resources/pictures/docx2_deru.png) |
| `形容` | 部分词尾为`い`的词语, 对应`形容词`或`第一类形容词` | `高*い` | `たか*い` | `0*-1` | `0*-1` | ![`docx0_takai`](./resources/pictures/docx0_takai.png) | ![`docx1_takai`](./resources/pictures/docx1_takai.png) | ![`docx2_takai`](./resources/pictures/docx2_takai.png) |
| `英語` | 支持大小写模糊 | `Time` | `タイム` | `1` | `0` | ![`docx0_time`](./resources/pictures/docx0_time.png) | ![`docx1_time`](./resources/pictures/docx1_time.png) | ![`docx2_time`](./resources/pictures/docx2_time.png) |
| `固有` | 专有名词, 尤其是混用`汉字`, `假名`, `字母`或是其它符号的名词 | `DECO/$*/27`([转义字符](#转义字符)) | `デコ//ニーナ` | `1/-1/1` | `0` | ![`docx0_deco27`](./resources/pictures/docx0_deco27.png) | ![`docx1_deco27`](./resources/pictures/docx1_deco27.png) | ![`docx2_deco27`](./resources/pictures/docx2_deco27.png) |
| `サ変` | 部分词尾为`する`的词语, 对应`サ行变格活用动词`或`第三类动词` | `接する` | `せっ*する` | `0*-1` | `0*-1` | ![`docx0_sessuru`](./resources/pictures/docx0_sessuru.png) | ![`docx1_sessuru`](./resources/pictures/docx1_sessuru.png) | ![`docx2_sessuru`](./resources/pictures/docx2_sessuru.png) |
| `カ変` | 动词`来る`, 即对应`カ行变格活用动词`或`第三类动词` | `来る` | `くる` | `0` | `0` | ![`docx0_kuru`](./resources/pictures/docx0_kuru.png) | ![`docx1_kuru`](./resources/pictures/docx1_kuru.png) | ![`docx2_kuru`](./resources/pictures/docx2_kuru.png) |

## 字典

可以按照指定的列标签搜索已经保存的词语, 只要输入框的内容属于对应列元素的子串即可匹配. 其中, 使用`Japanese`或`Kana`时, 匹配去除划分字符后的字符串. 可以通过`Find`按钮或者`Enter`按键触发搜索. 

可以根据词语在字典中的`ID`删除对应的词语. 可以通过`Delete`按钮或者`Enter`按键触发搜索. 

## 输入

除了普通的文本之外, 本软件设计了一些特殊方式实现便捷注音. 
1. 将不希望注音的部分用两个`#`包裹, 在执行注音过程的时候将不会对这部分内容进行注音. 在这个部分内, 请不要使用[转义字符](#转义字符). 
2. 对于不希望加入字典的注音(比如限定在某些特殊文本内的读法), 可以采用`(Japanese;Kana;Division0;Division1)`的格式进行注音, 分割标准与收入进字典的词语一致, 词性视作`固有`. 
3. 对于存在多种`Kana`注音的`Japanese`(如`明日`常见读作`あした`和`あす`), 使用优先级区分, 如果在字典中`あした`的优先级为`0`, `あす`的优先级为`1`, 则一般情况下, 注音为`あした`, 如果需要切换此处的优先级, 将`[Priority]`(此处为`[1]`)即可. 

## 词语添加

在词语添加组件中, 填写或选择对应内容完成之后, 点击下方的`Add`按钮, 如果程序判断符合前述划分规则, 词语即成功被添加入字典中. 

本软件提供了`自动划分(Auto Divide)`功能, 在填入`Japanese`, `Kana`, `Type`的情况下, 对于所有非`固有`和`英語`词性的词语, 如果`Japanese`和`Kana`中不存在除了`汉字`, `假名`, `阿拉伯数字`之外的字符, 或者对于`英語`词性的词语, 如果`Japanese`中不存在除了`英文字母`之外的字符且`Kana`中不存在除了`假名`之外的字符, `自动划分(Auto Divide)`会自动给出所有符合划分规则的可能组合. 可以选择合适的组合之后点击下方的`Apply Auto Division`按钮, 此时选择的划分会填入对应位置, 再按下`Add`即将词语添加进字典中. 

当可能的`自动划分`组合个数过多(设定为多于`2000`个)或`固有`词性的词语中含有非`汉字`, `假名`, `阿拉伯数字`, `英文字母`字符时, `自动划分(Auto Divide)`功能将不会被执行. 此时建议用户进行手动划分. 

`自动划分`中的`Division0`中的注音形式按照[推荐分割方式](#推荐分割方式)给出. 

## 转义字符

在[输入](#输入)和[词语添加](#词语添加)部分中, 为了实现某些特定的功能, 我们引入了一些字符([输入](#输入)中为`#`, `(`, `)`, `[`, `]`, [词语添加](#词语添加)中为`/`, `\`, `*`), 如果在这些场景下希望使用这些字符, 请在对应字符之前添加字符`$`, 例如在[输入](#输入)中的`$#`会被认为`#`, 而不实现跳过注音的功能. 对于`$`字符本身, 请使用`$$`. 

不严格的字符使用方式暂未做出明确的处理方式, 可能导致输出的结果与预期不符. 

## 方向键导航

本软件为了提高输入效率, 允许使用方向键在输入框、下拉框和按钮之间切换, 以及一些其它键盘行为. 
忽略控件本身的宽度, 控件在方向键导航中的`坐标`以左上角的控件为原点. 

本软件中共有`2`组控件组. 
1. [字典](#字典). 
2. [词语添加](#词语添加)

对于`3`种控件的具体描述如下: 
1. `输入框(LineEdit)`允许输入文本. 
2. `按钮(Button)`. 当焦点位于按钮上时按钮的样式会发生改变. 此时按下`Enter`键可以触发按钮的点击事件. 
3. `下拉框(ComboBox)`. 当焦点位于下拉框上时下拉框的样式会发生改变. 当下拉框未弹出时, 按下方向键可以聚焦至邻近控件, 当下拉框弹出时, 按下`上方向键`和`下方向键`可以切换当前的选项, 按下`左方向键`和`右方向键`可以在选项过长的时候水平滚动选项. 按下`Enter`键可以切换下拉框的弹出状态. 

## 推荐分割方式

1. 对于`英語`词性的词语, `Division0`为`1`. 
2. 对于分割中的单个汉字, `Division0`为`0`.
3. 对于分割中的多个汉字, 当其对应假名数与字数相等时, `Division0`为`2`, 否则为`1`. 


## 待完成任务

1. 帮助文档的完善
2. 预览功能的实现