"""Visual tokens shared by the map and the operations dashboard."""
REDESIGN_STYLES = """
<style>
/* One shared header geometry; content changes color between views. */
[data-testid="stMainBlockContainer"]{max-width:1680px!important;padding:0.65rem 2rem 2rem!important}
.st-key-common_header{height:76px!important;min-height:76px!important;max-height:76px!important;gap:24px!important}
.st-key-dashboard_header{margin-bottom:12px!important;gap:4px!important}
.st-key-dashboard_header::before{background:#20252b!important}
.st-key-dashboard_navigation [data-testid="stRadioGroup"]{gap:28px!important;flex-wrap:wrap!important}
.st-key-dashboard_navigation [data-testid="stRadioOption"]{padding:11px 2px 13px!important}
.st-key-dashboard_navigation [data-testid="stRadioOption"] p{font-size:15px!important}
.st-key-dashboard_navigation [data-testid="stRadioOption"]:has(input:checked){border-bottom-color:#f4c542!important}
.st-key-dashboard_navigation [data-testid="stRadioOption"]:has(input:checked) p{color:white!important}
.brand-name{font-size:23px!important;letter-spacing:-.035em!important}
.brand-sub{font-size:13px!important}
.st-key-common_header .st-key-user_brand{height:70px!important;min-height:70px!important}
.st-key-common_header .st-key-header_actions{height:70px!important}
.st-key-dashboard_management button{background:#343b42!important;color:#f8fafb!important;border:1px solid #59616a!important;border-radius:9px!important}

/* Customer search: a compact filter stack beside the live map. */
.st-key-map_workspace{gap:10px!important}
.st-key-map_workspace [data-testid="stHorizontalBlock"]{gap:18px}
.st-key-search_controls{padding:20px!important;gap:12px!important;border:1px solid #e2e7eb!important;border-radius:16px!important;background:#fff;box-shadow:0 4px 22px #26313c08}
.cp-search-title{font-size:22px;font-weight:750;letter-spacing:-.045em;color:#20252b;line-height:1.4}
.cp-search-sub{font-size:13px;color:#78848e;margin-top:3px;line-height:1.5}
.st-key-search_controls [data-testid="stWidgetLabel"] p{font-size:14px!important;font-weight:650;color:#313b45}
.st-key-search_controls input{font-size:14px!important}
.st-key-search_controls [data-testid="stRadioGroup"]{gap:12px!important;flex-wrap:wrap!important}
.st-key-search_controls [data-testid="stRadioOption"] p{font-size:14px!important}
.st-key-search_controls [data-testid="stExpander"]{border:1px solid #e1e6ea;border-radius:10px!important}
.st-key-search_controls button[kind="primary"]{min-height:44px!important;background:#252a31!important;border-color:#252a31!important}
.st-key-result_list{gap:10px!important}
.st-key-result_list_header [data-testid="stWidgetLabel"] p{font-size:12px!important;color:#7c8791}
.cp-result-title{font-size:17px;font-weight:750;color:#242b32;line-height:1.4;padding-top:20px}
.cp-result-title b{color:#252b32}
.st-key-result_scroll{padding:0 2px!important;scrollbar-width:thin;scrollbar-color:#bcc5cd transparent}
[class*="st-key-result_item_"]{background:#fff!important;border:1px solid #e1e6ea!important;border-radius:13px!important;padding:12px 14px!important;gap:3px!important}
[class*="st-key-result_item_"] [data-testid="stButton"] button{border:0!important;background:transparent!important;box-shadow:none!important;padding:0!important;min-height:26px!important;text-align:left!important;justify-content:flex-start!important}
[class*="st-key-result_item_"] [data-testid="stButton"] p{font-size:15px!important;font-weight:750!important;color:#20272f!important;line-height:1.4!important}
[class*="st-key-result_item_"] [data-testid="stCaptionContainer"] p{font-size:12px!important;color:#7c8995!important;line-height:1.45}
.cp-result-meta{display:flex;flex-wrap:wrap;gap:5px;margin-top:3px}
.cp-result-chip{display:inline-block;padding:4px 7px;border-radius:6px;background:#f1f4f6;color:#526270;font-size:11px;font-weight:650;line-height:1.4}
.cp-result-chip.ok{background:#eaf5ef;color:#287353}.cp-result-chip.warn{background:#fff5df;color:#996400}
.cp-result-empty{padding:30px 16px;border:1px dashed #d9e0e5;border-radius:12px;text-align:center;color:#83909b;font-size:13px;line-height:1.7}
.st-key-map_view [data-testid="stIFrame"]{border:0!important}
.st-key-results_pager{gap:12px!important;margin-top:8px!important}
.st-key-results_pager button{min-height:34px!important;padding:5px 12px!important;font-size:12px!important}

/* Chat window floats above the map, with distinct collapsed and expanded sizes. */
.st-key-chat_launcher{position:fixed!important;z-index:999!important;right:28px!important;bottom:24px!important;width:auto!important}
.st-key-chat_launcher button{background:#252b32!important;color:white!important;border:0!important;border-radius:999px!important;padding:12px 20px!important;box-shadow:0 10px 30px #1f283533!important}
.st-key-floating_chat_compact,.st-key-floating_chat_expanded{
 position:fixed!important;z-index:999!important;right:28px!important;bottom:24px!important;
 width:min(410px,calc(100vw - 36px))!important;max-height:calc(100vh - 90px)!important;overflow:auto!important;
 padding:15px!important;gap:8px!important;background:#fff!important;border:1px solid #dbe2e7!important;
 border-radius:16px!important;box-shadow:0 16px 48px #1a273028!important}
.st-key-floating_chat_expanded{width:min(620px,calc(100vw - 36px))!important}
.cp-chat-title{font-size:16px;font-weight:750;color:#252b32;white-space:nowrap;line-height:38px}
.cp-chat-title span{display:inline-grid;place-items:center;width:32px;height:32px;margin-right:8px;border-radius:10px;background:#252b32;color:#f6c940}
:is(.st-key-chat_expand,.st-key-chat_collapse) button{width:36px!important;min-width:36px!important;height:36px!important;min-height:36px!important;padding:0!important;border:0!important;background:#f2f4f6!important;border-radius:9px!important;color:#5c6874!important}
:is(.st-key-chat_expand,.st-key-chat_collapse) button p{display:none!important}
.st-key-chat_history{padding:4px!important;border:0!important;scrollbar-width:thin;scrollbar-color:#c2cbd2 transparent}
.st-key-chat_history [data-testid="stChatMessage"]{padding:10px 6px!important}
.st-key-chat_history [data-testid="stChatMessage"] p{font-size:14px!important;line-height:1.55!important}
:is(.st-key-floating_chat_compact,.st-key-floating_chat_expanded) [data-testid="stChatInput"]{margin:0!important}

/* Operations: restrained black / yellow, consistent state colors and clear data scopes. */
.st-key-operations_content{gap:14px!important}
.cp-scope{font-size:12px;color:#73808c;line-height:1.5;margin-top:2px}
.cp-scope span{margin-left:12px;color:#a0a9b1}
.cp-dashboard-title{display:flex;align-items:center;gap:12px}
.cp-dashboard-title>span{width:5px;height:25px;border-radius:5px;background:#e7b825}
.cp-dashboard-title h2{padding:0!important;margin:0!important;font-size:24px!important;line-height:1.4!important;font-weight:750!important;color:#222831!important}
.cp-dashboard-updated{text-align:right;color:#798692;font-size:12px;white-space:nowrap}
.cp-dashboard-updated b{font-weight:600;color:#52606d}
.cp-metric{min-height:112px;height:100%;padding:18px 20px;background:#fff;border:1px solid #e0e6ea;border-radius:13px;box-shadow:0 3px 14px #17253107}
.cp-metric-title{font-size:13px;color:#687784;font-weight:650}.cp-metric-value{font-size:26px;line-height:1.3;color:#20252b;font-weight:750;margin:10px 0 7px;font-variant-numeric:tabular-nums}
.cp-metric-sub{font-size:12px;color:#85919b}.cp-metric-sub.good{color:#2c805e}.cp-metric-sub.warn{color:#9a6a0e}.cp-metric-sub.bad{color:#b34a43}
.st-key-operations_content [data-testid="stHorizontalBlock"]{gap:16px!important}
.st-key-operations_content [data-testid="stVerticalBlockBorderWrapper"]{border-color:#e0e6ea!important;border-radius:13px!important}
.st-key-operations_content [data-testid="stVerticalBlock"][data-border="true"]{padding:18px 20px!important;gap:8px!important;border-radius:13px!important;min-width:0}
.cp-section-title{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:26px;flex-wrap:wrap}
.cp-section-title h3{padding:0!important;margin:0!important;font-size:16px!important;line-height:1.5!important;font-weight:750!important;color:#25303a!important}
.cp-section-note{font-size:11px;color:#8995a0;white-space:nowrap}
.cp-chart-empty{min-height:150px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:#9aa5ae;font-size:13px}
.cp-empty-icon{display:grid;place-items:center;width:34px;height:34px;border:1px solid #e2e7eb;border-radius:50%;color:#b3bdc5;font-size:18px}
.cp-provider-list{display:flex;flex-direction:column}.cp-provider-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #eff2f4;font-size:13px;color:#36434f}
.cp-provider-row:last-child{border-bottom:0}.cp-provider-status{display:flex;align-items:center;gap:6px;color:#72808c;text-align:right;font-size:12px}.cp-provider-status i{width:6px;height:6px;border-radius:50%;background:#a7b2bc;flex:none}.cp-provider-status.bad{color:#ad514b}.cp-provider-status.bad i{background:#d76a5f}
.cp-check-tag{padding:4px 8px;border-radius:6px;background:#f1f3f5;color:#64717d;font-size:12px}
.cp-pipeline{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;padding:8px 0}
.cp-pipeline-step{min-width:0;display:flex;align-items:center;gap:9px;padding:11px 10px;border:1px solid #e5e9ec;border-radius:9px;background:#fafbfb}
.cp-pipeline-index{display:grid;place-items:center;flex:none;width:27px;height:27px;border-radius:9px;background:#fff5cf;color:#896200;font-size:11px;font-weight:750}
.cp-pipeline-step b,.cp-pipeline-step small{display:block;overflow-wrap:anywhere}.cp-pipeline-step b{font-size:12px;line-height:1.4;color:#313a42}.cp-pipeline-step small{margin-top:3px;color:#89949e;font-size:10px;line-height:1.4}
.cp-pipeline.compact{gap:5px}.cp-pipeline.compact .cp-pipeline-step{padding:8px 6px;gap:5px}.cp-pipeline.compact .cp-pipeline-index{width:23px;height:23px}.cp-pipeline.compact .cp-pipeline-step b{font-size:11px}
.cp-inline-note{font-size:13px;color:#7b8995;line-height:1.6}
.cp-flow-pills{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:20px 0}.cp-flow-pills span{padding:7px 12px;border:1px solid #e4e9ed;border-radius:8px;background:#f8fafb;font-size:13px;color:#44515d}.cp-flow-pills i{color:#b3bdc5;font-style:normal}
.cp-event-row{display:grid;grid-template-columns:90px 1fr auto 80px;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid #edf0f2;font-size:12px;color:#70808c}.cp-event-row:last-child{border-bottom:0}.cp-event-row b{font-weight:650;color:#384652}.cp-event-row>span:last-child{text-align:right;font-variant-numeric:tabular-nums}.cp-event-state.warn{color:#a56d0d}.cp-event-state.bad{color:#bd5148}
@media(max-width:1000px){.cp-pipeline{grid-template-columns:repeat(3,minmax(0,1fr))}.cp-pipeline.compact{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:700px){
 [data-testid="stMainBlockContainer"]{padding:.4rem 1rem 1.5rem!important}
 .st-key-dashboard_navigation [data-testid="stRadioGroup"]{gap:15px!important}
 .st-key-floating_chat_compact,.st-key-floating_chat_expanded{right:12px!important;bottom:12px!important;width:calc(100vw - 24px)!important;max-height:calc(100vh - 70px)!important}
 .st-key-chat_launcher{right:14px!important;bottom:14px!important}
 .cp-dashboard-updated{text-align:left}.cp-metric{min-height:90px}.cp-metric-value{font-size:22px}
 .cp-pipeline{grid-template-columns:repeat(2,minmax(0,1fr))}
}

.cp-capture-dialog{position:fixed;inset:0;margin:auto;width:min(380px,calc(100vw - 36px));padding:26px;border:1px solid #e0e6ea;border-radius:16px;background:#fff;color:#27313a;box-shadow:0 18px 60px #11182738;font-family:"Pretendard Variable","Malgun Gothic",sans-serif}
.cp-capture-dialog::backdrop{background:#18212b66}
.cp-capture-mark{display:grid;place-items:center;width:36px;height:36px;border-radius:12px;background:#fff2c8;color:#8c6200;font-weight:750}
.cp-capture-dialog h2{font-size:19px;margin:15px 0 8px;line-height:1.4}
.cp-capture-dialog p{font-size:14px;line-height:1.7;color:#62707d;margin:0 0 22px}
.cp-capture-confirm{width:100%;border:0;border-radius:9px;padding:11px;background:#252a31;color:#fff;font-size:14px;font-weight:650;cursor:pointer}
.cp-capture-confirm:focus-visible{outline:3px solid #eab62f;outline-offset:2px}

.cp-metric{display:flex;align-items:flex-start;gap:14px}
.cp-metric-icon{flex:0 0 40px;width:40px;height:40px;display:grid;place-items:center;border-radius:11px;background:#fff7d9;color:#8d6b10}
.cp-metric-icon svg{width:21px;height:21px}
.cp-metric-content{min-width:0}
@media(max-width:700px){.cp-metric-icon{width:34px;height:34px;flex-basis:34px}.cp-metric{gap:10px}}

/* Brand, navigation and actions share one desktop header row. */
.st-key-dashboard_header{position:relative!important;top:auto!important}
.st-key-dashboard_header .st-key-common_header{gap:22px!important;flex-wrap:nowrap!important}
.st-key-dashboard_header .st-key-user_brand{
 flex:0 0 300px!important;width:300px!important;min-width:300px!important;max-width:300px!important;
}
.st-key-header_navigation{
 flex:1 1 0%!important;min-width:0!important;width:auto!important;
 height:70px;align-items:center!important;gap:18px!important;flex-wrap:nowrap!important;
}
.st-key-header_menu{flex:1 1 0%!important;min-width:0!important;width:auto!important}
.st-key-header_navigation .st-key-dashboard_navigation [data-testid="stRadioGroup"]{
 flex-wrap:nowrap!important;gap:clamp(12px,1.5vw,25px)!important;
}
.st-key-header_navigation .st-key-dashboard_navigation [data-testid="stRadioOption"]{
 white-space:nowrap;padding:12px 0!important;
}
.st-key-header_navigation .st-key-dashboard_navigation [data-testid="stRadioOption"] p{font-size:14px!important}
.st-key-dashboard_management{flex:0 0 auto!important;width:auto!important}
@media(max-width:1280px){
 .st-key-dashboard_header .st-key-common_header{
  height:auto!important;min-height:76px!important;max-height:none!important;flex-wrap:wrap!important;row-gap:0!important;
 }
 .st-key-dashboard_header .st-key-user_brand{
  flex:1 1 0%!important;width:auto!important;min-width:0!important;max-width:none!important;order:0;
 }
 .st-key-dashboard_header .st-key-header_actions{order:1}
 .st-key-dashboard_header .st-key-header_navigation{
  order:2;flex:0 0 100%!important;width:100%!important;height:auto;min-height:54px;
 }
}
@media(max-width:700px){
 .st-key-header_navigation{flex-wrap:wrap!important;gap:6px!important;padding-bottom:8px}
 .st-key-header_menu{flex:1 1 100%!important}
 .st-key-header_navigation .st-key-dashboard_navigation [data-testid="stRadioGroup"]{flex-wrap:wrap!important;gap:12px!important}
 .st-key-header_navigation .st-key-dashboard_navigation [data-testid="stRadioOption"] p{font-size:13px!important}
}

/* Consistent inline brand on the entry, search and operations screens. */
.cp-brand-copy{display:flex;align-items:center;gap:14px;min-width:0}
.cp-brand-copy .dashboard-marker{display:none}
.st-key-common_header .cp-brand-copy .brand-name,.brand-row .cp-brand-copy .brand-name{
 font-size:21px!important;line-height:1.3!important;font-weight:750!important;margin:0!important;white-space:nowrap;
}
.st-key-common_header .cp-brand-copy .brand-sub,.brand-row .cp-brand-copy .brand-sub{
 font-size:12px!important;line-height:1.4!important;margin:0!important;white-space:nowrap;
}
.st-key-dashboard_header .st-key-user_brand{
 flex:0 0 450px!important;width:450px!important;min-width:450px!important;max-width:450px!important;
}

/* Three balanced overview summaries, with legible labels and consistent spacing. */
.st-key-operations_content{gap:18px!important}
.cp-dashboard-title h2{font-size:26px!important;line-height:1.4!important}
.cp-dashboard-subtitle{margin:5px 0 4px 17px;font-size:13px;line-height:1.5;color:#73808c}
.cp-dashboard-updated{font-size:13px}
.cp-overview-card{
 box-sizing:border-box;display:flex;flex-direction:column;gap:0;min-height:250px;height:100%;
 padding:24px 26px;background:#fff;border:1px solid #dfe5e9;border-radius:14px;
 box-shadow:0 5px 18px #1c293308;
}
.cp-overview-heading{display:flex;align-items:center;gap:12px;margin-bottom:22px}
.cp-overview-heading h3{padding:0!important;margin:0!important;font-size:18px!important;line-height:1.45!important;font-weight:750!important;color:#27313a!important}
.cp-overview-number{display:grid;place-items:center;width:34px;height:34px;flex:none;border-radius:10px;background:#fff6d8;color:#8f6b08;font-size:12px;font-weight:750}
.cp-overview-metric{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.cp-overview-metric span{font-size:14px;color:#6d7a86;font-weight:600}
.cp-overview-metric strong{font-size:27px;line-height:1.3;font-weight:750;color:#222a31;font-variant-numeric:tabular-nums}
.cp-overview-metric strong.good{color:#257b59}.cp-overview-metric strong.warn{color:#a36c0c}.cp-overview-metric strong.bad{color:#b64740}
.cp-overview-details{display:flex;flex-direction:column;gap:8px;padding-top:19px}
.cp-overview-detail{font-size:14px;line-height:1.5;color:#566573}
.cp-overview-footer{margin-top:auto;padding-top:18px;color:#83909b;font-size:12px;line-height:1.5}
.cp-section-title h3{font-size:18px!important;line-height:1.5!important}
.cp-section-note{font-size:12px}
.cp-metric-title{font-size:14px}.cp-metric-value{font-size:28px}.cp-metric-sub{font-size:13px}
.cp-provider-row{font-size:14px}.cp-provider-status{font-size:13px}
.cp-chart-empty{font-size:14px;color:#7c8994}
.cp-inline-note{font-size:14px;line-height:1.6}

/* Align the floating chat with the same content edge as the map and header. */
.st-key-floating_chat_compact,.st-key-floating_chat_expanded,.st-key-chat_launcher{
 right:max(2rem,calc((100vw - 1680px)/2 + 2rem))!important;
}
:is(.st-key-chat_expand,.st-key-chat_collapse) button{
 border:1px solid #dce3e8!important;background:#f6f8f9!important;color:#52616d!important;
 border-radius:50%!important;
}
:is(.st-key-chat_expand,.st-key-chat_collapse) button:hover{background:#e9edf0!important;color:#232b32!important}
@media(max-width:1420px){
 .st-key-dashboard_header .st-key-common_header{
  height:auto!important;min-height:76px!important;max-height:none!important;flex-wrap:wrap!important;row-gap:0!important;
 }
 .st-key-dashboard_header .st-key-user_brand{
  flex:1 1 0%!important;width:auto!important;min-width:0!important;max-width:none!important;order:0;
 }
 .st-key-dashboard_header .st-key-header_actions{order:1}
 .st-key-dashboard_header .st-key-header_navigation{order:2;flex:0 0 100%!important;width:100%!important;height:auto;min-height:54px}
}
@media(max-width:700px){
 .cp-brand-copy{gap:8px}
 .st-key-common_header .cp-brand-copy .brand-name,.brand-row .cp-brand-copy .brand-name{font-size:18px!important}
 .st-key-common_header .cp-brand-copy .brand-sub,.brand-row .cp-brand-copy .brand-sub{font-size:11px!important;white-space:normal}
 .st-key-floating_chat_compact,.st-key-floating_chat_expanded,.st-key-chat_launcher{right:1rem!important}
 .cp-overview-card{min-height:210px;padding:20px}
 .cp-overview-heading{margin-bottom:15px}
 .cp-overview-metric strong{font-size:24px}
}

/* Keep the entry header unchanged and make only the access form more compact. */
.st-key-login-form{max-width:480px!important;padding:20px!important}
.st-key-login-form [data-testid="stTextInput"] [data-baseweb="input"]{min-height:44px!important}
.st-key-login-form [data-testid="stFormSubmitButton"] button{min-height:44px!important}

/* Overview selectors switch summaries without changing the main navigation. */
.st-key-overview_axis [data-testid="stRadioGroup"]{
 display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px!important;width:100%!important;
}
.st-key-overview_axis [data-testid="stRadioOption"]{
 box-sizing:border-box;display:flex!important;align-items:flex-start;min-width:0;min-height:112px;
 padding:20px 22px!important;border:1px solid #dfe5e9!important;border-radius:14px!important;
 background:#fff!important;box-shadow:0 5px 18px #1c293308;cursor:pointer;
}
.st-key-overview_axis [data-testid="stRadioOption"]>div>div:first-child{display:none!important}
.st-key-overview_axis [data-testid="stRadioOption"] p{font-size:16px!important;line-height:1.5!important;color:#28313a!important;font-weight:700!important}
.st-key-overview_axis [data-testid="stRadioOption"] [data-testid="stCaptionContainer"] p{font-size:13px!important;line-height:1.5!important;color:#76838f!important;font-weight:400!important}
.st-key-overview_axis [data-testid="stRadioOption"]:has(input:checked),
.st-key-overview_axis [data-testid="stRadioOption"][data-selected="true"]{
 border-color:#d9aa24!important;background:#fffaf0!important;box-shadow:0 4px 16px #ad870d16;
}
.st-key-overview_axis [data-testid="stRadioOption"]:focus-within{outline:2px solid #d9aa24;outline-offset:2px}
.cp-summary-panel{margin-top:18px;padding:24px 26px;border:1px solid #dfe5e9;border-radius:14px;background:#fff;box-shadow:0 5px 18px #1c293308}
.cp-summary-header{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
.cp-summary-header h3{font-size:18px!important;line-height:1.4!important;font-weight:750!important;margin:0!important;padding:0!important;color:#26313a!important}
.cp-summary-header>span{font-size:12px;color:#788692}
.cp-summary-fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));margin-top:22px}
.cp-summary-field{display:flex;flex-direction:column;gap:8px;min-width:0;padding:0 20px;border-right:1px solid #edf0f2}
.cp-summary-field:first-child{padding-left:0}.cp-summary-field:last-child{border-right:0}
.cp-summary-field span{font-size:13px;color:#6e7c88}.cp-summary-field strong{font-size:25px;color:#232b32;line-height:1.3;font-weight:750;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.cp-summary-fields.good .cp-summary-field:first-child strong{color:#257b59}
.cp-summary-fields.warn .cp-summary-field:first-child strong{color:#a36c0c}
.cp-summary-fields.bad .cp-summary-field:first-child strong{color:#b64740}
.cp-summary-note{margin-top:20px;padding-top:14px;border-top:1px solid #edf0f2;color:#73818d;font-size:13px;line-height:1.5}
@media(max-width:700px){
 .st-key-overview_axis [data-testid="stRadioGroup"]{grid-template-columns:1fr!important;gap:8px!important}
 .st-key-overview_axis [data-testid="stRadioOption"]{min-height:76px;padding:14px 16px!important}
 .cp-summary-panel{padding:20px}.cp-summary-fields{gap:10px}.cp-summary-field{padding:0 10px}
 .cp-summary-field strong{font-size:19px}
}

/* Shared, readable brand and understated action buttons without moving the header. */
.st-key-common_header .cp-brand-copy .brand-name{font-size:25px!important;line-height:1.3!important}
.st-key-common_header .cp-brand-copy .brand-sub{font-size:14px!important;line-height:1.4!important}
.st-key-dashboard_header .st-key-user_brand{flex-basis:510px!important;width:510px!important;min-width:510px!important;max-width:510px!important}
.st-key-common_header :is(.st-key-header_settings,.st-key-header_power) button{
 border-radius:14px!important;border:1px solid #e3e7eb!important;background:#f7f8f9!important;color:#34404a!important;box-shadow:none!important;
}
.st-key-common_header :is(.st-key-header_settings,.st-key-header_power) button:hover{background:#e9edf0!important;border-color:#d7dde2!important}
.st-key-dashboard_header .st-key-common_header :is(.st-key-header_settings,.st-key-header_power) button{background:#323a43!important;border-color:#48515a!important;color:#f6f8fa!important}
.st-key-dashboard_header .st-key-common_header :is(.st-key-header_settings,.st-key-header_power) button:hover{background:#454e58!important}

/* Keep chat actions grouped inside its own header. */
.st-key-chat_header{align-items:center!important;flex-wrap:nowrap!important;gap:8px!important;width:100%!important}
.st-key-chat_header :is(.st-key-chat_expand,.st-key-chat_collapse){flex:0 0 36px!important;width:36px!important;min-width:36px!important;max-width:36px!important}
.st-key-chat_header :is(.st-key-chat_expand,.st-key-chat_collapse) button{
 width:36px!important;min-width:36px!important;max-width:36px!important;height:36px!important;min-height:36px!important;max-height:36px!important;
 display:flex!important;align-items:center!important;justify-content:center!important;border:1px solid #e1e6ea!important;
 border-radius:10px!important;background:#f7f8f9!important;color:#596773!important;padding:0!important;box-shadow:none!important;
}
.st-key-chat_header :is(.st-key-chat_expand,.st-key-chat_collapse) button:hover{background:#e9edf0!important;color:#252c33!important}
.st-key-chat_header :is(.st-key-chat_expand,.st-key-chat_collapse) button p{display:block!important;position:absolute!important;width:1px!important;height:1px!important;overflow:hidden!important;clip-path:inset(50%)!important}
.st-key-chat_header :is(.st-key-chat_expand,.st-key-chat_collapse) button [data-testid="stIconMaterial"]{font-size:19px!important}

/* A zero-layout-size script host stays mounted while the sidebar is collapsed. */
.st-key-capture_listener,[data-testid="stVerticalBlockBorderWrapper"]:has(> .st-key-capture_listener){display:none!important}

/* Entry image is cropped without distorting the car or changing the access form. */
.st-key-login_layout{max-width:1080px!important;margin:clamp(24px,6vh,72px) auto 32px!important}
.st-key-login_visual [data-testid="stImage"] img{width:100%!important;height:min(600px,68vh)!important;min-height:390px;object-fit:cover;object-position:center 62%;border-radius:20px;display:block}
.st-key-login_layout .st-key-login-form{max-width:480px!important}
@media(max-width:1420px){
 .st-key-dashboard_header .st-key-user_brand{flex:1 1 0%!important;width:auto!important;min-width:0!important;max-width:none!important}
}
@media(max-width:700px){
 .st-key-common_header .cp-brand-copy .brand-name{font-size:21px!important}
 .st-key-common_header .cp-brand-copy .brand-sub{font-size:13px!important;white-space:normal}
 .st-key-login_layout{margin:12px auto 24px!important}
 .st-key-login_visual [data-testid="stImage"] img{height:260px!important;min-height:0;object-position:center 65%}
}


/* Refined cards and readable spacing */
.st-key-operations_content {gap:22px!important;}
.st-key-operations_content [data-testid="stVerticalBlock"][data-border="true"] {box-sizing:border-box!important;border-radius:18px!important;border-color:#e3e8ef!important;box-shadow:0 8px 28px #25364c0b!important;padding:20px!important;}
.cp-metric {border-radius:18px!important;min-height:128px!important;padding:22px!important;box-shadow:0 8px 25px #2634470b!important;}
.cp-metric-icon {background:#fff5d9!important;border:1px solid #f5e6bd!important;}
.cp-chart-empty {color:#8190a1!important;background:#f8fafc!important;border-radius:14px!important;}
.cp-pipeline-step {border-radius:12px!important;background:#f8fafc!important;}
.cp-result-chip.speed {background:#eaf3ff;color:#3b6798}.cp-result-chip.distance {background:#f0ecfb;color:#705a99}
.cp-result-chip.ok {background:#e4f5ed;color:#24785b}.cp-result-chip.warn {background:#fff2d9;color:#8b6819}
.cp-chat-title {display:flex;align-items:center;gap:8px;line-height:1.3!important}.cp-chat-title span {margin:0!important;flex:none;display:grid!important;place-items:center!important;line-height:1!important}
.cp-search-space {height:10px}
.st-key-search_controls [data-testid="stTextInput"] {margin-bottom:12px}


.st-key-common_header .cp-brand-copy .brand-name{font-size:27px!important}
.st-key-common_header .cp-brand-copy .brand-sub{font-size:15px!important}
@media(max-width:700px){.st-key-common_header .cp-brand-copy .brand-name{font-size:20px!important}.st-key-common_header .cp-brand-copy .brand-sub{font-size:12px!important}}


.st-key-header_navigation .st-key-dashboard_navigation [data-testid="stRadioOption"] p {font-size:17px!important;line-height:1.45!important}
@media(max-width:700px){.st-key-header_navigation .st-key-dashboard_navigation [data-testid="stRadioOption"] p {font-size:15px!important}}

/* Center the chat controls independently of Streamlit icon spacing. */
:is(.st-key-chat_expand,.st-key-chat_collapse) button {display:flex!important;align-items:center!important;justify-content:center!important;gap:0!important}
:is(.st-key-chat_expand,.st-key-chat_collapse) button [data-testid="stIconMaterial"] {margin:0!important;display:block!important;line-height:1!important}

/* Align the shared brand text with the center of the lightning icon. */
.st-key-common_header .st-key-user_brand {align-items:center!important}
.st-key-common_header .cp-brand-copy {position:relative;top:-6px;align-items:center!important}
.st-key-common_header .cp-brand-copy .brand-name,.st-key-common_header .cp-brand-copy .brand-sub {margin:0!important}

/* Compact dashboard toolbar and permission summary. */
.st-key-dashboard_toolbar{display:flex!important;justify-content:flex-end!important;align-items:center!important;gap:12px!important;flex-wrap:wrap!important;margin:10px 0 24px!important}
.st-key-dashboard_period_control{align-items:center!important;gap:10px!important}
.cp-toolbar-label{font-size:13px;font-weight:650;color:#677482;white-space:nowrap}
.st-key-dashboard_period [data-testid="stRadioGroup"]{display:flex;gap:4px!important;flex-wrap:nowrap!important;background:#f2f4f6;border-radius:10px;padding:4px}
.st-key-dashboard_period [data-testid="stRadioOption"]{padding:6px 10px!important;border-radius:7px;white-space:nowrap}
.st-key-dashboard_period [data-testid="stRadioOption"] > div:first-child{display:none!important}
.st-key-dashboard_period [data-testid="stRadioOption"]:has(input:checked){background:white;box-shadow:0 1px 4px #25364c1b}
.st-key-dashboard_period [data-testid="stRadioOption"] p{font-size:13px!important;color:#536170!important}
.st-key-dashboard_refresh button{min-height:36px!important;border:1px solid #dce3e9!important;border-radius:10px!important;background:#fff!important;padding:6px 12px!important}
.cp-dashboard-updated{white-space:nowrap;font-size:12px;color:#7b8794}.cp-dashboard-updated b{color:#475766;font-weight:650}
.cp-role-list{display:grid;gap:9px;margin-top:12px}.cp-role-item{display:flex;align-items:center;gap:14px;padding:14px 16px;background:#f7f9fb;border:1px solid #e8edf1;border-radius:13px}.cp-role-symbol{display:grid;place-items:center;flex:none;width:36px;height:36px;border-radius:11px;background:#fff3d5;color:#9c741b;font-size:12px;font-weight:750}.cp-role-item strong{display:block;font-size:15px;color:#26313c}.cp-role-item p{margin:4px 0 0;color:#667687;font-size:13px;line-height:1.5}.cp-role-note{margin-top:14px;color:#8794a1;font-size:12px;line-height:1.5}
.cp-chart-empty{box-sizing:border-box!important;padding:24px!important;margin-top:12px!important;min-height:130px!important}
@media(max-width:700px){.st-key-dashboard_toolbar{justify-content:flex-start!important}.cp-dashboard-updated{text-align:left!important}}

/* Clear, spacious dashboard rows and quiet empty states. */
.st-key-operations_content{padding:8px 0 32px!important}
:is(.st-key-flow_kpis,.st-key-system_kpis,.st-key-pipeline_kpis){margin:20px 0 30px!important}
:is(.st-key-flow_charts,.st-key-flow_details,.st-key-system_charts,.st-key-system_details,.st-key-pipeline_details,.st-key-pipeline_flow){margin:0 0 28px!important}
:is(.st-key-flow_kpis,.st-key-system_kpis,.st-key-pipeline_kpis,.st-key-flow_charts,.st-key-flow_details,.st-key-system_charts,.st-key-system_details,.st-key-pipeline_details) [data-testid="stHorizontalBlock"]{gap:20px!important;align-items:stretch!important}
.st-key-operations_content [data-testid="stVerticalBlock"][data-border="true"]{padding:24px!important;gap:14px!important;overflow:visible!important;min-height:170px}
.cp-metric{min-height:142px!important;padding:24px!important;border-radius:18px!important;box-shadow:0 5px 20px #2736450b!important}
.cp-metric-value{margin:12px 0 10px!important;font-size:29px!important}
.cp-section-title{margin-bottom:8px;gap:16px}.cp-section-title h3{font-size:18px!important}.cp-section-note{font-size:12px!important}
.cp-chart-empty{background:transparent!important;margin:0!important;min-height:132px!important;padding:18px!important;color:#84919d!important}
.cp-empty-icon{background:#f6f8fa;border:0!important;color:#9daab5!important}
.st-key-overview_axis{margin:18px 0 24px!important}.st-key-overview_axis [data-testid="stRadioGroup"]{gap:20px!important}
.st-key-overview_axis [data-testid="stRadioOption"]{min-height:72px!important;align-items:center!important;padding:18px 22px!important;border-radius:16px!important}
.cp-summary-panel{margin:0 0 26px!important;padding:28px!important;border-radius:18px!important}.cp-summary-fields{margin-top:24px!important}.cp-summary-note{margin-top:24px!important}
.cp-provider-row{padding:13px 0!important}.cp-pipeline{gap:10px!important}.cp-pipeline-step{padding:14px!important}
@media(max-width:700px){.st-key-operations_content [data-testid="stVerticalBlock"][data-border="true"]{padding:18px!important}.cp-metric{min-height:112px!important;padding:18px!important}.st-key-overview_axis [data-testid="stRadioOption"]{min-height:60px!important}.cp-summary-panel{padding:20px!important}}
/* Subtle neumorphic treatment for existing icon controls. */
.brand-bolt, .st-key-status_bolt button[data-testid="stPopoverButton"], .cp-chat-title span {
    background:linear-gradient(145deg,#30363e,#242930)!important;
    box-shadow:inset 1px 1px 2px #ffffff18,inset -1px -1px 2px #10141955,0 2px 5px #1d29321c!important;
}
:is(.st-key-header_settings,.st-key-header_power) button,
.st-key-chat_header :is(.st-key-chat_expand,.st-key-chat_collapse) button {
    background:linear-gradient(145deg,#fafbfc,#eef1f4)!important;
    border:1px solid #dbe2e8!important;
    box-shadow:2px 2px 5px #cbd2d866,-2px -2px 5px #ffffffcc!important;
    transition:box-shadow .15s ease,background .15s ease!important;
}
[data-testid="stMain"]:has(.dashboard-marker) :is(.st-key-header_settings,.st-key-header_power) button {
    background:linear-gradient(145deg,#424a53,#333b44)!important;
    border-color:#606b76!important;
    box-shadow:2px 2px 5px #15191e80,-1px -1px 3px #ffffff12!important;
    color:#fff!important;
}
:is(.st-key-header_settings,.st-key-header_power,.st-key-chat_expand,.st-key-chat_collapse) button:active {
    box-shadow:inset 2px 2px 4px #9ba7b54d,inset -2px -2px 4px #ffffff80!important;
}

/* Page title and dashboard controls share one responsive row. */
.st-key-dashboard_page_heading{align-items:center!important;justify-content:space-between!important;gap:24px!important;margin:12px 0 22px!important;flex-wrap:wrap!important}
.st-key-dashboard_heading_title{flex:1 1 260px!important;min-width:220px!important}
.st-key-dashboard_toolbar{flex:0 1 auto!important;width:auto!important;justify-content:flex-end!important;margin:0!important;gap:10px!important}
.st-key-dashboard_period_control{flex:0 0 auto!important;width:auto!important}
.st-key-operations_content{padding-top:0!important}
.st-key-overview_axis{margin:0 0 32px!important}
.st-key-overview_axis [data-testid="stRadioOption"]{min-height:66px!important}
@media(max-width:900px){.st-key-dashboard_page_heading{gap:12px!important}.st-key-dashboard_toolbar{justify-content:flex-start!important;flex-wrap:wrap!important}}

/* Align the page title and compact controls on the same Streamlit row. */
.st-key-dashboard_page_heading{margin:0 0 14px!important;overflow:visible!important}
.st-key-dashboard_page_heading [data-testid="stHorizontalBlock"]{align-items:center!important;gap:12px!important}
.st-key-dashboard_page_heading [data-testid="stColumn"]{min-width:0!important}
.st-key-dashboard_toolbar{margin:0!important;gap:8px!important;justify-content:flex-end!important;align-items:center!important}
.st-key-dashboard_period_control{gap:8px!important;align-items:center!important}
.st-key-dashboard_page_heading .cp-dashboard-title{margin:0!important}
.st-key-dashboard_page_heading .cp-dashboard-subtitle{display:block!important;margin:5px 0 0 17px!important;line-height:1.5!important;overflow:visible!important}
.st-key-overview_axis{margin:0 0 22px!important}
@media(max-width:900px){.st-key-dashboard_toolbar{justify-content:flex-start!important}}

/* Keep the permissions action legible against the dark dashboard header. */
.st-key-dashboard_header .st-key-menu_roles button{min-height:44px!important;padding:0 14px!important;display:flex!important;align-items:center!important;justify-content:center!important;gap:7px!important;background:#323a43!important;border:1px solid #59616a!important;border-radius:12px!important;color:#f6f8fa!important;opacity:1!important}
.st-key-dashboard_header .st-key-menu_roles button p,.st-key-dashboard_header .st-key-menu_roles button [data-testid="stIconMaterial"]{color:#f6f8fa!important;opacity:1!important}
.st-key-dashboard_header .st-key-menu_roles button:hover{background:#454e58!important;border-color:#77818c!important}
/* Pin the icon glyph to the actual center of each chat button. */
.st-key-chat_header :is(.st-key-chat_expand,.st-key-chat_collapse) button { position:relative!important; }
.st-key-chat_header :is(.st-key-chat_expand,.st-key-chat_collapse) button [data-has-shortcut] { position:static!important; }
.st-key-chat_header :is(.st-key-chat_expand,.st-key-chat_collapse) button [data-testid="stIconMaterial"] {
 position:absolute!important; left:50%!important; top:50%!important; transform:translate(-50%,-50%)!important;
 width:20px!important; height:20px!important; display:grid!important; place-items:center!important; line-height:1!important; margin:0!important;
}
.cp-reference-link { display:inline-flex; align-items:center; position:relative; z-index:2; pointer-events:auto; min-height:36px; padding:0 12px; border:1px solid #d5dce3; border-radius:10px; background:#fff; color:#29343e!important; text-decoration:none!important; font-size:13px; }
.cp-reference-link:hover { background:#f1f4f6; border-color:#aebac5; }
</style>
"""
