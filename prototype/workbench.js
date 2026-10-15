import {ClaimReviewClient, ClaimApiError} from "/api-client.js?v=20261015g";

const api = new ClaimReviewClient();
const $ = (id) => document.getElementById(id);
const statusNames = {completed:"Đã chạy",completed_precomputed:"Trường chuẩn bị sẵn",unavailable:"Chưa kích hoạt",skipped_missing_input:"Thiếu đầu vào",blocked_missing_input:"Thiếu dữ liệu bảng",error:"Gặp lỗi",skipped_optional:"Không yêu cầu",partial:"Chưa đầy đủ"};
const moduleNames = {tabular_risk:"Xếp hạng hồ sơ",document_pipeline:"Đọc chứng từ",damage_segmentation:"Ảnh hư hỏng",media_authenticity:"Nguồn gốc ảnh",consistency:"Đối chiếu thông tin",relationships:"Quan hệ hồ sơ",guided_capture:"Ảnh chụp hướng dẫn"};
const categoryNames = {risk:"Điểm ưu tiên",damage:"Ảnh xe",document:"Chứng từ",consistency:"Đối chiếu",relationship:"Quan hệ",authenticity:"Nguồn gốc ảnh"};
const priorityNames = {normal:"Thông thường",review:"Cần rà soát",high:"Ưu tiên cao"};
const analysisNames = {complete:"Đủ module",partial:"Phân tích một phần",blocked:"Chưa chấm được"};
const damageNames = {crack:"Nứt",dent:"Móp",scratch:"Trầy xước","glass shatter":"Kính vỡ","lamp broken":"Đèn vỡ","tire flat":"Lốp xẹp"};
const documentTypeNames = {questionnaire:"Biểu mẫu / bảng hỏi",form:"Biểu mẫu",invoice:"Hóa đơn",letter:"Thư",memo:"Biên bản / ghi nhớ",email:"Email",handwritten:"Tài liệu viết tay"};
const evidenceTypeNames = {
  "claim-intake":"Thông tin khai báo ban đầu",
  vehicle_image:"Ảnh hiện trạng và hư hỏng của xe",
  claim_document:"Chứng từ bồi thường (biên bản, báo giá hoặc hóa đơn)",
  rear_wide_angle_photo:"Ảnh toàn cảnh phía sau xe",
};
const featureGroupNames = {
  policy:"thông tin hợp đồng bảo hiểm", customer:"thông tin người được bảo hiểm",
  incident:"thông tin sự cố", claim_cost:"chi phí/yêu cầu bồi thường",
  vehicle:"thông tin phương tiện", other:"dữ liệu nghiệp vụ khác",
};
const damageColors = {crack:"#9c4f96",dent:"#167f74",scratch:"#d45555","glass shatter":"#4f6ccf","lamp broken":"#c78619","tire flat":"#7259a8"};
const formatNumber = (value) => value == null ? "—" : new Intl.NumberFormat("vi-VN").format(value);
const formatBytes = (value) => value == null ? "—" : value < 1024*1024 ? `${(value/1024).toFixed(1)} KB` : `${(value/1024/1024).toFixed(2)} MB`;
let claimId = "";
let analysis = null;

const evidenceTypeName = (value) => evidenceTypeNames[value] || value.replaceAll("_"," ");
const signalForEvidence = (a,evidenceId) => (a.signals||[]).filter(signal=>signal.severity!=="info"&&(signal.evidence_ids||[]).includes(evidenceId));
const severityLabel = (severity) => severity==="high"?"CỜ MỨC CAO":severity==="review"?"CẦN RÀ SOÁT":"THÔNG TIN";

function setError(message) { const box=$("errorBox"); box.textContent=message; box.hidden=!message; }
function openTab(name) {
  document.querySelectorAll(".tabs button").forEach(button=>button.classList.toggle("active",button.dataset.tab===name));
  document.querySelectorAll(".panel").forEach(panel=>panel.classList.toggle("active",panel.id===name));
}
document.querySelectorAll(".tabs button").forEach(button=>button.addEventListener("click",()=>openTab(button.dataset.tab)));

function signalExplanation(signal) {
  if(signal.category==="consistency"&&signal.explanation.includes("amount_mismatch")) return "Số tiền trên chứng từ khác số tiền khai báo; cần xem bản gốc và xác nhận lại.";
  if(signal.category==="authenticity"&&signal.explanation.includes("matches evidence")) return "Ảnh này trùng hoặc rất giống bằng chứng đã xuất hiện ở hồ sơ khác.";
  return signal.explanation;
}

function signalImpact(signal) {
  const impacts={
    authenticity:"Bằng chứng có thể đã được dùng lại hoặc thiếu thông tin nguồn gốc. Đây là lý do xác minh thêm, chưa phải kết luận ảnh giả.",
    damage:"Vùng hư hỏng cần được đối chiếu với mô tả tai nạn, ảnh ở góc khác và báo giá sửa chữa.",
    document:"Thông tin đọc từ chứng từ có thể ảnh hưởng đến số tiền, ngày sự cố hoặc nhận dạng phương tiện.",
    consistency:"Hai nguồn thông tin chưa khớp; nếu không xác nhận, hồ sơ có thể được xử lý dựa trên dữ liệu sai.",
    relationship:"Thực thể dùng chung giúp mở rộng phạm vi điều tra nhưng không tự chứng minh có gian lận.",
    risk:"Hồ sơ được đưa lên trước trong hàng chờ để người duyệt tập trung nguồn lực có hạn.",
  };
  return impacts[signal.category]||"Cần đối chiếu với bằng chứng gốc trước khi quyết định.";
}

function signalAction(signal) {
  const actions={
    authenticity:"Mở ảnh gốc, xem hồ sơ trùng và yêu cầu chụp mới có hướng dẫn nếu cần.",
    damage:"Xem vùng được khoanh, kiểm tra thêm các góc chụp và so sánh với báo giá.",
    document:"Đọc chứng từ gốc và sửa trường OCR/KIE nếu hệ thống đọc sai.",
    consistency:"Xác nhận nguồn đúng, lưu chỉnh sửa và ghi lý do trong nhật ký.",
    relationship:"Mở sơ đồ quan hệ và kiểm tra thời điểm hình thành liên kết.",
    risk:"Rà soát hồ sơ theo quy trình; không dùng riêng điểm số để từ chối.",
  };
  return actions[signal.category]||"Chuyển người duyệt kiểm tra bằng chứng liên quan.";
}

function deriveBusiness(a) {
  const high=a.signals.filter(signal=>signal.severity==="high");
  const primary=high[0]||a.signals.find(signal=>signal.severity==="review")||a.signals[0];
  const missingModules=Object.entries(a.module_status||{}).filter(([,value])=>!["completed","completed_precomputed","skipped_optional"].includes(value.status));
  let action="Tiếp tục xử lý",headline="Chưa có tín hiệu nổi bật cần ưu tiên",next="Đọc bằng chứng gốc và hoàn tất quy trình duyệt thông thường.";
  if(high.length||a.priority==="high") {action="Rà soát chuyên sâu";headline=primary?.title||"Hồ sơ nằm trong nhóm ưu tiên cao";next=primary?signalAction(primary):"Mở các bằng chứng được gắn cờ trước khi quyết định.";}
  else if(a.analysis_status!=="complete"||a.missing_evidence?.length) {action="Yêu cầu bổ sung";headline=primary?.title||"Chưa đủ dữ liệu để kết luận";next=primary?signalAction(primary):"Bổ sung ảnh, chứng từ hoặc dữ liệu nghiệp vụ còn thiếu.";}
  else if(primary) {action="Cần rà soát";headline=primary.title;next=signalAction(primary);}
  const finding=primary?signalExplanation(primary):"Không có tín hiệu tự động nào được ghi nhận trong phạm vi module đã chạy.";
  const impact=primary?signalImpact(primary):"Không có tín hiệu không đồng nghĩa hồ sơ chắc chắn bình thường; người duyệt vẫn cần kiểm tra bằng chứng.";
  const gaps=missingModules.map(([key,value])=>`${moduleNames[key]||key}: ${moduleDetail(key,value)}`);
  return {action,headline,next,finding,impact,gaps};
}

function renderBusiness(a) {
  const business=deriveBusiness(a);
  $("actionValue").textContent=business.action;
  $("actionReason").textContent=a.human_review_required?"Cần người duyệt xác nhận":"Có thể tiếp tục theo quy trình";
  $("businessHeadline").textContent=business.headline;
  $("businessBadge").textContent=priorityNames[a.priority]||a.priority;
  $("businessWhy").textContent="Đề xuất dựa trên phần dữ liệu đã có; phần chưa chạy được hiển thị riêng để tránh tạo cảm giác chắc chắn giả.";
  $("businessFinding").textContent=business.finding;
  $("businessImpact").textContent=business.impact;
  $("businessNext").textContent=business.next;
  $("businessGaps").textContent=business.gaps.length?`Chưa được kiểm tra tự động: ${business.gaps.join(" · ")}`:"Các module cần thiết cho hồ sơ này đã hoàn tất.";
}

function renderModules(a) {
  const entries = Object.entries(a.module_status || {});
  $("moduleSummary").textContent = `${entries.filter(([,x])=>x.status.startsWith("completed")).length}/${entries.length} phần đã chạy`;
  const list = $("moduleList"); list.replaceChildren();
  entries.forEach(([key,value])=>{
    const card=document.createElement("div"); card.className=`module ${value.status}`;
    const title=document.createElement("b"); const dot=document.createElement("span"); dot.className="dot";
    title.append(dot,document.createTextNode(moduleNames[key]||key));
    const detail=document.createElement("small"); detail.textContent=moduleDetail(key,value);
    card.append(title,detail); list.append(card);
  });
}

function moduleDetail(key,value) {
  const status=statusNames[value.status]||value.status;
  if(value.status==="completed_precomputed") return "Trường demo đã chuẩn bị sẵn; chưa đọc tệp bằng OCR/KIE.";
  if(key==="damage_segmentation" && value.status==="unavailable") return "Chưa có checkpoint YOLO trên máy demo.";
  if(key==="document_pipeline" && value.status==="unavailable") return "Chưa có checkpoint chứng từ trên máy demo.";
  if(key==="guided_capture" && value.status==="skipped_optional") return "Chưa dùng bước chụp ảnh hướng dẫn.";
  if(value.status==="skipped_missing_input") return "Chưa có bằng chứng đầu vào cho module này.";
  if(value.status==="blocked_missing_input") {
    const count=value.missing_field_count;
    const groups=(value.missing_business_groups||[]).map(group=>featureGroupNames[group]||group);
    return `${count?`Thiếu ${count} trường`:`Thiếu dữ liệu`} để xếp hạng${groups.length?`: ${groups.join(", ")}`:""}.`;
  }
  return status;
}

function renderScoreDetails(a) {
  const status=a.module_status?.tabular_risk||{}, missing=status.missing_field_count||0;
  const required=status.required_field_count||0, provided=status.provided_field_count||0;
  const groups=(status.missing_business_groups||[]).map(group=>featureGroupNames[group]||group);
  const fields=status.missing_fields||[];
  if(a.research_risk_score==null){
    $("scoreStatus").textContent="Không đủ dữ liệu để xếp hạng";
    $("scoreStatus").className="score-state blocked";
    $("scoreReason").textContent=missing
      ? `Model cần ${required} trường đã được khóa từ lúc huấn luyện, nhưng hồ sơ mới có ${provided}; còn thiếu ${missing} trường${groups.length?` thuộc ${groups.join(", ")}`:""}. Bỏ trống điểm an toàn hơn việc tự điền hoặc đoán dữ liệu.`
      : "Dữ liệu bảng không đúng schema mà model đã được huấn luyện; hệ thống chủ động không tạo điểm.";
    $("scoreStillWorks").textContent="Ảnh xe, nguồn gốc ảnh, chứng từ, luật đối chiếu và quan hệ vẫn chạy độc lập khi có đầu vào. Hồ sơ vẫn có thể được đưa lên ưu tiên nếu các phần này phát sinh cờ.";
    $("scoreNext").textContent="Không cần người dùng nhập JSON. Hệ thống nghiệp vụ hoặc backend phải bổ sung các trường còn thiếu; hiện tại hãy xử lý theo cờ và bằng chứng gốc.";
    $("scoreTechnical").textContent=fields.length?fields.join(", "):status.reason||"API chưa trả danh sách trường thiếu.";
  } else {
    $("scoreStatus").textContent="Đã xếp hạng hàng chờ";
    $("scoreStatus").className="score-state ready";
    $("scoreReason").textContent=`Model đã nhận đủ ${required||provided||"các"} trường trong schema tabular_v1 và tạo điểm ${(a.research_risk_score*100).toFixed(1)}/100.`;
    $("scoreStillWorks").textContent="Điểm này chạy song song với ảnh, chứng từ, đối chiếu và quan hệ. Một cờ mức cao vẫn có thể đẩy hồ sơ lên trước dù điểm XGBoost thấp.";
    $("scoreNext").textContent="Dùng điểm để sắp thứ tự xem hồ sơ. Không đọc nó như xác suất gian lận và không dùng riêng điểm này để từ chối bồi thường.";
    $("scoreTechnical").textContent=`Phiên bản tabular_v1 · ${provided||required||"đủ"}/${required||provided||"đủ"} trường model · output là điểm xếp hạng nghiên cứu.`;
  }
}

function renderSignals(a) {
  const list=$("signals"); list.replaceChildren();
  if (!a.signals.length) { const empty=document.createElement("div");empty.className="empty";empty.textContent="Chưa có tín hiệu được ghi nhận. Hãy vẫn xem ảnh và chứng từ gốc.";list.append(empty);return; }
  a.signals.forEach(signal=>{
    const card=document.createElement("article");card.className=`signal ${signal.severity}`;
    const flag=document.createElement("div");flag.className=`signal-flag ${signal.severity}`;flag.textContent=`${signal.severity==="info"?"●":"⚑"} ${severityLabel(signal.severity)}`;
    const category=document.createElement("div");category.className="category";category.textContent=categoryNames[signal.category]||signal.category;
    const title=document.createElement("h3");title.textContent=signal.title;
    const observed=document.createElement("div");observed.className="signal-block";const observedLabel=document.createElement("b");observedLabel.textContent="Phát hiện";const observedText=document.createElement("p");observedText.textContent=signalExplanation(signal);observed.append(observedLabel,observedText);
    const impact=document.createElement("div");impact.className="signal-block";const impactLabel=document.createElement("b");impactLabel.textContent="Ý nghĩa nghiệp vụ";const impactText=document.createElement("p");impactText.textContent=signalImpact(signal);impact.append(impactLabel,impactText);
    const action=document.createElement("div");action.className="signal-block action";const actionLabel=document.createElement("b");actionLabel.textContent="Nên làm gì";const actionText=document.createElement("p");actionText.textContent=signalAction(signal);action.append(actionLabel,actionText);
    const technical=document.createElement("details");technical.className="signal-technical";const summary=document.createElement("summary");summary.textContent="Chi tiết kỹ thuật";const techText=document.createElement("p");const confidence=signal.confidence==null?"không công bố":`${(signal.confidence*100).toFixed(1)}%`;techText.textContent=`Model: ${signal.model_name||"rule/system"} · Version: ${signal.model_version||"—"} · Confidence: ${confidence}`;technical.append(summary,techText);
    const button=document.createElement("button");button.type="button";button.textContent="Xem phần liên quan →";
    const tab=signal.category==="relationship"?"relations":["document","consistency","damage","authenticity"].includes(signal.category)?"evidence":"overview";
    button.addEventListener("click",()=>openTab(tab));card.append(flag,category,title,observed,impact,action,technical,button);list.append(card);
  });
}

function addOverlay(container, image, data, kind) {
  if (!data?.length) return;
  image.addEventListener("load",()=>{
    const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
    svg.setAttribute("viewBox",`0 0 ${image.naturalWidth} ${image.naturalHeight}`);
    svg.setAttribute("preserveAspectRatio","xMidYMid meet");
    for (const item of data) {
      let shape;
      const color=kind==="damage"?(damageColors[item.class_name]||"#16a88c"):kind==="field"?"#b66a12":"#287a9f";
      if (kind==="damage" && item.mask_polygon?.length) {
        shape=document.createElementNS("http://www.w3.org/2000/svg","polygon");
        shape.setAttribute("points",item.mask_polygon.map(point=>point.join(",")).join(" "));
      } else {
        const box=kind==="damage"?item.box_xyxy:item.bbox && [item.bbox.x1,item.bbox.y1,item.bbox.x2,item.bbox.y2];
        if (!box || box.length!==4) continue;
        shape=document.createElementNS("http://www.w3.org/2000/svg","rect");
        shape.setAttribute("x",box[0]);shape.setAttribute("y",box[1]);shape.setAttribute("width",box[2]-box[0]);shape.setAttribute("height",box[3]-box[1]);
      }
      shape.setAttribute("fill",kind==="damage"?`${color}55`:kind==="field"?"#d6a34333":"#287a9f12");shape.setAttribute("stroke",color);shape.setAttribute("stroke-width",kind==="ocr"?"1.25":"3");
      shape.setAttribute("vector-effect","non-scaling-stroke");svg.append(shape);
      if(kind==="damage"&&item.box_xyxy?.length===4){
        const [x,y]=item.box_xyxy;const label=`${damageNames[item.class_name]||item.class_name} ${Math.round((item.confidence||0)*100)}%`;
        const group=document.createElementNS("http://www.w3.org/2000/svg","g");
        const text=document.createElementNS("http://www.w3.org/2000/svg","text");text.setAttribute("x",x+5);text.setAttribute("y",Math.max(16,y+15));text.setAttribute("fill","#fff");text.setAttribute("font-size","13");text.setAttribute("font-weight","700");text.textContent=label;
        const background=document.createElementNS("http://www.w3.org/2000/svg","rect");background.setAttribute("x",x);background.setAttribute("y",Math.max(0,y));background.setAttribute("width",Math.max(86,label.length*7.2));background.setAttribute("height","20");background.setAttribute("rx","3");background.setAttribute("fill",color);background.setAttribute("opacity",".94");
        group.append(background,text);svg.append(group);
      }
    }
    container.append(svg);
  },{once:true});
}

function authenticitySummary(report) {
  if(!report) return {verdict:"Chưa kiểm tra",basis:"Chưa có kết quả phân tích nguồn gốc ảnh.",action:"Chạy kiểm tra trên file ảnh gốc."};
  const detected=(report.findings||[]).filter(item=>item.outcome==="detected");
  const ai=detected.filter(item=>item.code.startsWith("ai_metadata_marker")||item.code==="c2pa_ai_assertion_present");
  const edited=detected.filter(item=>item.code.startsWith("editing_software_marker"));
  const forensic=detected.filter(item=>item.code.startsWith("forensic_model_"));
  const reuse=detected.find(item=>item.code==="cross_claim_image_reuse");
  const provenanceProblem=detected.find(item=>item.code==="c2pa_validation_problem");
  if(ai.length) return {verdict:"Có dấu hiệu AI được khai báo",basis:`Phát hiện ${ai.length} marker AI trong metadata hoặc Content Credentials. Marker là căn cứ nguồn gốc cần xác minh, chưa tự chứng minh có gian lận.`,action:"Kiểm tra Content Credentials/metadata, đối chiếu hồ sơ liên quan và yêu cầu file camera gốc nếu quy trình cần."};
  if(provenanceProblem) return {verdict:"Nguồn gốc ký số có vấn đề",basis:"Content Credentials có manifest nhưng quá trình xác minh chữ ký/chuỗi tin cậy không đạt. Cần kiểm tra file gốc và trust policy.",action:"Kiểm tra chữ ký, lịch sử chỉnh sửa và yêu cầu file gốc."};
  if(reuse) {
    const matches=report.image_info?.cross_claim_matches||[];
    const exact=matches.filter(item=>item.match_type==="exact").length;
    const claims=[...new Set(matches.map(item=>item.claim_id).filter(Boolean))];
    return {verdict:"Ảnh đã xuất hiện ở hồ sơ khác",basis:`Tìm thấy ${matches.length} kết quả trùng${exact?`, gồm ${exact} bản trùng byte`:""}${claims.length?`. Hồ sơ liên quan: ${claims.join(", ")}`:""}. Đây là dấu hiệu tái sử dụng bằng chứng, chưa phải kết luận gian lận.`,action:"Mở hồ sơ trùng và yêu cầu ảnh chụp mới có hướng dẫn nếu cần."};
  }
  if(forensic.length) return {verdict:"Pixel forensic đề nghị rà soát",basis:"Model pixel forensic đã hiệu chuẩn vượt ngưỡng rà soát. Đây là tín hiệu sàng lọc, không phải chứng cứ độc lập về ảnh AI.",action:"Xem đây là tín hiệu sàng lọc; đối chiếu file gốc, Content Credentials, chuỗi tiếp nhận và ảnh chụp mới."};
  if(edited.length) return {verdict:"Metadata khai báo phần mềm chỉnh sửa",basis:`Phát hiện ${edited.length} dấu phần mềm chỉnh sửa trong metadata. Dấu vết này chưa cho biết vùng nào đã thay đổi hoặc thay đổi có hợp lệ hay không.`,action:"Yêu cầu file camera gốc hoặc ảnh chụp mới có hướng dẫn; đối chiếu hash và hồ sơ liên quan."};
  return {verdict:"Chưa đủ bằng chứng xác định ảnh AI",basis:"Không tìm thấy marker AI đã xác minh. Metadata hoặc watermark có thể bị xóa khi ảnh được gửi qua ứng dụng khác.",action:"Không kết luận thật/giả. Dùng file gốc, chụp có hướng dẫn và đối chiếu các bằng chứng khác."};
}

function authenticityChecks(report) {
  const findings=report?.findings||[];
  const has=predicate=>findings.some(predicate);
  const outcome=predicate=>findings.find(predicate)?.outcome;
  return [
    ["Metadata camera/EXIF",has(item=>item.code==="metadata_absent")?"Không tìm thấy":"Có dữ liệu đọc được","Thiếu EXIF có thể do mạng xã hội hoặc re-encode; không chứng minh ảnh giả."],
    ["Content Credentials/C2PA",has(item=>item.code==="c2pa_unavailable")?"Chưa kiểm tra được":has(item=>item.code==="c2pa_validation_problem")?"Có vấn đề":"Không có cảnh báo đã xác minh","Chữ ký hợp lệ giúp truy nguồn; không có chữ ký không chứng minh ảnh thật."],
    ["Marker AI được khai báo",has(item=>item.code.startsWith("ai_metadata_marker")||item.code==="c2pa_ai_assertion_present")?"Đã phát hiện":"Không tìm thấy","Marker có thể bị xóa, nên kết quả âm tính không loại trừ ảnh AI."],
    ["Dấu phần mềm chỉnh sửa",has(item=>item.code.startsWith("editing_software_marker"))?"Đã phát hiện":"Không tìm thấy","Nếu có, hệ thống chỉ biết phần mềm được khai báo, chưa biết pixel nào bị sửa."],
    ["Tái sử dụng giữa hồ sơ",outcome(item=>item.code==="cross_claim_image_reuse")==="detected"?"Đã phát hiện":"Chưa phát hiện","Ảnh trùng/gần trùng là lý do điều tra thêm, chưa tự chứng minh gian lận."],
    ["Pixel forensic đúng miền",has(item=>item.code==="forensic_model_not_configured")?"Chưa được kích hoạt":"Đã chạy model hiệu chuẩn","Chỉ được bật khi benchmark ảnh bảo hiểm và calibration gate đạt yêu cầu."],
    ["SynthID",has(item=>item.code==="synthid_provider_not_integrated")?"Chưa tích hợp provider":"Có kết quả provider","SynthID không phải marker phổ quát cho mọi công cụ tạo ảnh."],
  ];
}

function damageSummary(a,detections,imageCount) {
  const status=a.module_status?.damage_segmentation||{};
  if(!imageCount) return {title:"Chưa có ảnh xe",detail:"Không thể đánh giá hư hỏng khi chưa có ảnh.",action:"Yêu cầu ảnh toàn cảnh và cận cảnh."};
  if(detections.length) {
    const labels=[...new Set(detections.map(item=>damageNames[item.class_name]||item.class_name))];
    return {title:`Phát hiện ${detections.length} vùng cần xem`,detail:labels.join(", "),action:"Kiểm tra lớp phủ trên ảnh và đối chiếu với mô tả tai nạn/báo giá."};
  }
  if(status.status==="unavailable") return {title:"Chưa phân tích được hư hỏng",detail:"Checkpoint YOLO chưa được cài trên máy chủ. Đây không có nghĩa xe không hư hỏng.",action:"Cài checkpoint đúng hash hoặc chuyển giám định viên xem ảnh gốc."};
  if(status.status==="completed") return {title:"Không thấy vùng thuộc taxonomy hiện tại",detail:"Model chỉ biết sáu lớp CarDD và có thể bỏ sót hư hỏng ngoài miền.",action:"Người duyệt vẫn phải xem ảnh, đặc biệt với hư hỏng nặng hoặc loại chưa có nhãn."};
  return {title:"Chưa có kết quả phân tích hư hỏng",detail:status.reason||"Module chưa hoàn tất.",action:"Kiểm tra trạng thái module và ảnh đầu vào."};
}

function appendFlagBanner(parent,signals,label) {
  if(!signals.length)return;
  const high=signals.filter(signal=>signal.severity==="high").length;
  const banner=document.createElement("div");banner.className=`flag-banner ${high?"high":"review"}`;
  const icon=document.createElement("span");icon.textContent="⚑";
  const copy=document.createElement("div");
  const title=document.createElement("b");title.textContent=`${high?"Cờ mức cao":"Cần rà soát"} tại ${label}`;
  const detail=document.createElement("p");detail.textContent=signals.map(signal=>signal.title).join(" · ");
  copy.append(title,detail);banner.append(icon,copy);parent.append(banner);
}

function renderEvidence(a) {
  const images=a.evidence.filter(e=>e.kind==="image" && e.source_uri?.startsWith("runtime://"));
  const documents=a.evidence.filter(e=>e.kind==="document" && e.source_uri?.startsWith("runtime://"));
  const detections=a.extracted_fields?.damage_detections||[];
  const docResults=a.extracted_fields?.document_results||[];
  const authenticity=a.extracted_fields?.media_authenticity||[];
  const vehicle=$("vehiclePreview");vehicle.replaceChildren();vehicle.classList.remove("flagged-high","flagged-review");
  let imageFlags=[];
  if (images.length) {
    const img=document.createElement("img");img.alt="Ảnh xe đã nộp cho hồ sơ";img.src=api.evidenceContentUrl(a.claim_id,images[0].evidence_id);
    vehicle.append(img);addOverlay(vehicle,img,detections.filter(d=>d.evidence_id===images[0].evidence_id),"damage");
    const imageReport=authenticity.find(row=>row.evidence_id===images[0].evidence_id);
    imageFlags=signalForEvidence(a,images[0].evidence_id);
    vehicle.classList.add(imageFlags.some(signal=>signal.severity==="high")?"flagged-high":imageFlags.length?"flagged-review":"flagged-none");
    const info=imageReport?.image_info||{};
    $("vehicleMeta").textContent=`${images.length} ảnh · ${images[0].label} · ${info.width||"?"}×${info.height||"?"} px · ${formatBytes(images[0].size_bytes)}`;
  } else {vehicle.textContent="Hồ sơ này chưa có ảnh xe.";$("vehicleMeta").textContent="Không suy ra xe không hư hỏng khi thiếu ảnh.";}
  const damageList=$("damageResults");damageList.replaceChildren();
  appendFlagBanner(damageList,imageFlags,"ảnh xe này");
  const damage=damageSummary(a,detections,images.length);
  addResult(damageList,damage.title,damage.detail);
  if(images.length){
    const selected=detections.filter(item=>item.evidence_id===images[0].evidence_id);
    const grouped=Object.entries(selected.reduce((acc,item)=>{const key=item.class_name;acc[key]??=[];acc[key].push(item.confidence||0);return acc;},{}));
    addResult(damageList,"Tệp đã phân tích",`${images[0].label} · SHA-256 ${images[0].sha256?images[0].sha256.slice(0,12)+"…":"chưa có"}`);
    grouped.sort((a,b)=>Math.max(...b[1])-Math.max(...a[1])).forEach(([name,scores])=>addResult(damageList,damageNames[name]||name,`${scores.length} vùng · độ tin cậy cao nhất ${Math.round(Math.max(...scores)*100)}%`));
    if(grouped.length)addResult(damageList,"Cách đọc vùng khoanh","Màu và nhãn trên ảnh là vùng model đề nghị kiểm tra. Độ tin cậy không phải tỷ lệ thiệt hại hoặc xác suất gian lận.");
  }
  addResult(damageList,"Hành động với ảnh hư hỏng",damage.action);
  const auth=authenticitySummary(authenticity[0]);
  addResult(damageList,"Nguồn gốc ảnh",auth.verdict);
  addResult(damageList,"Căn cứ",auth.basis);
  if(authenticity[0]){
    const checklist=document.createElement("div");checklist.className="auth-checklist";
    const heading=document.createElement("h4");heading.textContent="Ảnh đang có và còn thiếu bằng chứng gì?";checklist.append(heading);
    authenticityChecks(authenticity[0]).forEach(([label,status,detail])=>{const row=document.createElement("div");const head=document.createElement("p");const b=document.createElement("b");b.textContent=label;const badge=document.createElement("span");badge.textContent=status;head.append(b,badge);const small=document.createElement("small");small.textContent=detail;row.append(head,small);checklist.append(row)});
    damageList.append(checklist);
  }
  addResult(damageList,"Hành động với nguồn gốc ảnh",auth.action);
  const preview=$("documentPreview");preview.replaceChildren();preview.classList.remove("flagged-high","flagged-review");
  let documentFlags=[];
  if (documents.length) {
    const evidence=documents[0];const url=api.evidenceContentUrl(a.claim_id,evidence.evidence_id);
    documentFlags=signalForEvidence(a,evidence.evidence_id);
    preview.classList.add(documentFlags.some(signal=>signal.severity==="high")?"flagged-high":documentFlags.length?"flagged-review":"flagged-none");
    if (evidence.label.toLowerCase().endsWith(".pdf")) {const frame=document.createElement("iframe");frame.src=url;frame.title="Chứng từ gốc";preview.append(frame);}
    else {
      const img=document.createElement("img");img.src=url;img.alt="Chứng từ gốc đã nộp";preview.append(img);
      const result=docResults.find(row=>row.document_id===evidence.evidence_id);
      addOverlay(preview,img,(result?.tokens||[]).filter(token=>token.page_number===1&&token.confidence>=0.55),"ocr");
      addOverlay(preview,img,(result?.fields||[]).filter(field=>field.page_number===1),"field");
    }
    $("documentMeta").textContent=`${documents.length} tệp · ${evidence.label} · ${formatBytes(evidence.size_bytes)} · SHA-256 ${evidence.sha256?evidence.sha256.slice(0,12)+"…":"chưa có"}`;
  } else {preview.textContent="Hồ sơ này chưa có chứng từ nhị phân.";$("documentMeta").textContent="Có thể vẫn có trường demo chuẩn bị sẵn.";}
  const fields=$("documentResults");fields.replaceChildren();
  appendFlagBanner(fields,documentFlags,"chứng từ này");
  if (docResults.length) {
    docResults.forEach(result=>{
      const tokens=result.tokens||[], extracted=result.fields||[];
      const readable=tokens.filter(token=>token.confidence>=0.55);
      const mean=readable.length?readable.reduce((sum,token)=>sum+(token.confidence||0),0)/readable.length:null;
      const documentType=documentTypeNames[result.document_type]||result.document_type||"Chưa xác định";
      addResult(fields,"Loại chứng từ model nhận dạng",`${documentType}${result.document_type?` (${result.document_type})`:""}${result.document_type_confidence==null?"":` · độ tin cậy ${Math.round(result.document_type_confidence*100)}%`}`);
      addResult(fields,"Kết quả đọc chữ (OCR)",`${tokens.length} vùng chữ · ${readable.length} vùng đạt ngưỡng hiển thị${mean==null?"":` · độ tin cậy trung bình ${Math.round(mean*100)}%`}. Khung xanh trên ảnh cho biết vị trí OCR đã đọc.`);
      if(readable.length){
        const excerpt=readable.slice(0,12).map(token=>token.text).join(" · ");
        addResult(fields,"Trích đoạn OCR",excerpt.length>320?`${excerpt.slice(0,320)}…`:excerpt);
      }
      if(extracted.length){
        const fieldNames={total_amount:"Tổng tiền",document_date:"Ngày chứng từ",plate_number:"Biển số xe",document_number:"Số chứng từ"};
        const methodNames={layoutlmv3:"LayoutLMv3",rule_fallback:"quy tắc dự phòng vì model chưa có kết quả",rule_override_low_confidence:"quy tắc được chọn vì model confidence thấp và hai bên mâu thuẫn",rule:"quy tắc xác định"};
        extracted.forEach(field=>addResult(fields,`Trường ${fieldNames[field.field_name]||field.field_name}`,`${field.normalized_value} · độ tin cậy ${field.confidence==null?"—":Math.round(field.confidence*100)+"%"} · nguồn: ${methodNames[field.method]||field.method||"không xác định"}`));
        const conflicts=(result.warnings||[]).filter(warning=>warning.startsWith("kie_model_rule_conflict:"));
        if(conflicts.length)addResult(fields,"⚑ Vì sao chứng từ có cờ",`Model học máy và quy tắc đọc chứng từ cho kết quả khác nhau ở ${conflicts.map(value=>fieldNames[value.split(":")[1]]||value.split(":")[1]).join(", ")}. Giá trị đang hiển thị đã đi qua chính sách confidence; người duyệt cần đối chiếu vùng khoanh với bản gốc trước khi lưu quyết định.`);
        addResult(fields,"Cách đọc khung chứng từ","Khung cam là trường có cấu trúc do KIE trích xuất; phải đối chiếu bản gốc trước khi dùng.");
      } else {
        addResult(fields,"Trường có cấu trúc","Chưa trích được ngày hoặc tổng tiền từ chứng từ này. Model KIE hiện được huấn luyện trên hóa đơn SROIE tiếng Anh, nên biên bản tai nạn tiếng Việt nằm ngoài miền đánh giá.");
        addResult(fields,"Hành động","Đọc bản gốc và nhập giá trị đã xác nhận vào phần bên dưới. Kết quả này được lưu vào nhật ký, không tự dùng để huấn luyện lại model.");
      }
    });
  } else if (a.module_status?.document_pipeline?.status==="completed_precomputed") {
    addResult(fields,"Trường demo chuẩn bị sẵn",`Tổng tiền: ${formatNumber(a.extracted_fields?.total_amount)} · Ngày: ${a.extracted_fields?.document_date||"—"}. Đây không phải output OCR/KIE của tệp vừa tải.`);
  } else {
    const documentStatus=a.module_status?.document_pipeline||{};
    const detail=documentStatus.status==="unavailable"?"Tệp đã được lưu nhưng model đọc chứng từ chưa được cài trên máy chủ.":documentStatus.reason||"Chưa có kết quả đọc chứng từ.";
    addResult(fields,"Trích xuất chứng từ",detail);
    addResult(fields,"Hành động",documents.length?"Người duyệt đọc bản gốc; sau khi bật OCR/KIE, xác nhận hoặc sửa các trường được trích xuất.":"Yêu cầu bổ sung chứng từ nếu quy trình nghiệp vụ cần.");
  }
  refreshCorrectionContext();
}

function addResult(parent,title,detail){const item=document.createElement("div");item.className="result-item";const head=document.createElement("b");head.textContent=title;const body=document.createElement("span");body.textContent=detail;item.append(head,body);parent.append(item);}

function currentFieldValue(fieldName) {
  const direct=analysis?.extracted_fields?.[fieldName];
  if(direct!==undefined&&direct!==null&&direct!=="")return direct;
  const aliases={total_amount:["total_amount","total","TOTAL"],document_date:["document_date","date","DATE"],plate_number:["plate_number","plate","license_plate"]};
  const fields=(analysis?.extracted_fields?.document_results||[]).flatMap(row=>row.fields||[]);
  return fields.find(item=>(aliases[fieldName]||[fieldName]).includes(item.field_name))?.normalized_value??null;
}

function refreshCorrectionContext() {
  const field=$("fieldName").value,value=currentFieldValue(field);
  $("correctionContext").textContent=value==null?"Hệ thống chưa trích xuất được trường này. Bạn vẫn có thể nhập giá trị đúng sau khi đọc chứng từ gốc.":`Giá trị hệ thống đang đọc: ${value}. Chỉ sửa khi đã đối chiếu trực tiếp với chứng từ gốc.`;
  $("correctedValue").placeholder=value==null?"Nhập theo chứng từ gốc":`Giá trị hiện tại: ${value}`;
}

function renderGraph(a) {
  const graph=a.graph_features||{}, box=$("graphMetrics"),brief=$("relationshipBrief"),relatedBox=$("relatedClaims"),alert=$("relationshipAlert"),typesBox=$("relationshipTypes"),checklist=$("relationshipChecklist"),actions=$("relationshipActions");
  [box,brief,relatedBox,alert,typesBox,checklist,actions].forEach(node=>node.replaceChildren());
  const relationSignals=(a.signals||[]).filter(signal=>signal.category==="relationship");
  if(graph.data_status==="not_provided") {
    alert.className="relationship-alert missing";alert.innerHTML="<span>!</span><div><b>Chưa thể đối chiếu với hồ sơ trước</b><p>Hồ sơ chưa có thông tin định danh dùng cho bước quan hệ.</p></div>";
    $("graphState").textContent="Chưa nhận được số điện thoại, biển số hoặc xưởng để đối chiếu. Đây là thiếu dữ liệu, không có nghĩa hồ sơ không liên quan.";
    addResult(brief,"Phần vẫn chạy","Ảnh, chứng từ và điểm xếp hạng vẫn được phân tích nếu có dữ liệu. Chỉ riêng bước tìm hồ sơ liên quan chưa thực hiện được.");
    addResult(brief,"Cần bổ sung gì","Biển số xe, số điện thoại liên hệ hoặc mã xưởng sửa chữa đã được xác minh trong hồ sơ nghiệp vụ.");
    addResult(brief,"Không được hiểu sai","Không có dữ liệu quan hệ không đồng nghĩa hồ sơ độc lập hoặc không có rủi ro.");
    return;
  }
  $("graphState").textContent="Hệ thống chỉ dùng liên kết đã tồn tại trước thời điểm chấm để tránh nhìn trước dữ liệu tương lai.";
  [["shared_entity_count","Thực thể dùng chung"],["two_hop_claim_count","Hồ sơ trong 2 bước liên kết"],["connected_component_size","Quy mô cụm liên kết"],["graph_degree","Số liên kết trực tiếp"]].forEach(([key,label])=>{
    const tile=document.createElement("div");tile.className="graph-metric";const number=document.createElement("strong");number.textContent=formatNumber(graph[key]);const name=document.createElement("span");name.textContent=label;tile.append(number,name);box.append(tile);
  });
  const related=graph.related_claim_ids||[], types=graph.shared_entity_types||[], entityDisplay=graph.query_entity_display||{};
  const labels=types.map(type=>{const name=({contact_phone:"Số điện thoại liên hệ",repair_shop:"Xưởng sửa chữa",vehicle_plate:"Biển số xe"}[type]||type);return entityDisplay[type]?`${name} (${entityDisplay[type]})`:name});
  if(related.length){
    const high=relationSignals.some(signal=>signal.severity==="high");
    alert.className=`relationship-alert ${high?"high":"review"}`;alert.innerHTML=`<span>⚑</span><div><b>${related.length} hồ sơ trước cần đối chiếu</b><p>Trùng ${labels.join(", ")||"thông tin liên hệ"}. Đây là đầu mối điều tra, chưa phải kết luận gian lận.</p></div>`;
    labels.forEach(label=>{const chip=document.createElement("span");chip.textContent=`✓ Trùng ${label}`;typesBox.append(chip)});
    addResult(brief,"Đã tìm thấy gì",`${related.length} hồ sơ cũ nằm trong cùng mạng liên kết và dùng chung ${labels.length} loại thông tin.`);
    addResult(brief,"Giá trị nghiệp vụ","Giúp người duyệt mở đúng hồ sơ cần so sánh thay vì dò thủ công toàn bộ kho claim.");
    addResult(brief,"Giới hạn","Hệ thống chỉ biết loại thông tin trùng; giá trị được băm trong graph để giảm lộ dữ liệu. Quan hệ hợp lệ vẫn có thể xảy ra.");
    related.forEach(id=>{
      const card=document.createElement("article");card.className="related-claim-card";
      const copy=document.createElement("div");const title=document.createElement("b");title.textContent=id;const detail=document.createElement("small");detail.textContent=`Dùng chung: ${labels.join(", ")||"thông tin liên kết"}`;copy.append(title,detail);
      const link=document.createElement("a");link.href=`/?view=workbench&claim_id=${encodeURIComponent(id)}&tab=relations`;link.textContent="Mở và đối chiếu →";card.append(copy,link);relatedBox.append(card);
    });
    const heading=document.createElement("h3");heading.textContent="4 câu hỏi cần trả lời trước khi quyết định";checklist.append(heading);
    ["Đây có đúng là cùng chủ xe, người liên hệ hoặc xưởng hợp lệ không?","Ngày sự cố giữa các hồ sơ có chồng lấn hoặc mâu thuẫn không?","Ảnh hay chứng từ có bị tái sử dụng giữa các hồ sơ không?","Nếu quan hệ hợp lệ, đã ghi rõ căn cứ vào nhật ký chưa?"].forEach((text,index)=>{const row=document.createElement("div");row.innerHTML=`<span>${index+1}</span><p>${text}</p>`;checklist.append(row)});
    const actionTitle=document.createElement("b");actionTitle.textContent="Chọn hướng xử lý sau khi đối chiếu:";actions.append(actionTitle);
    [["continue_processing","Quan hệ hợp lệ","Đã đối chiếu hồ sơ liên quan và xác nhận quan hệ dùng chung là hợp lệ."],["request_evidence","Cần thêm bằng chứng","Cần bổ sung bằng chứng để xác minh quan hệ dùng chung giữa các hồ sơ."],["special_review","Chuyển rà soát sâu","Quan hệ dùng chung có điểm chưa hợp lý, cần rà soát chuyên sâu."]].forEach(([decision,label,reason])=>{const button=document.createElement("button");button.type="button";button.textContent=label;button.addEventListener("click",()=>{const radio=document.querySelector(`input[name=decision][value=${decision}]`);if(radio)radio.checked=true;$("reviewReason").value=reason;$("reviewReason").focus();});actions.append(button)});
  } else {
    alert.className="relationship-alert clear";alert.innerHTML="<span>✓</span><div><b>Chưa thấy hồ sơ cũ dùng chung thông tin</b><p>Kết quả chỉ áp dụng cho kho dữ liệu hiện đang có.</p></div>";
    addResult(brief,"Kết quả đối chiếu","Chưa thấy hồ sơ trước đó dùng chung biển số, số điện thoại hoặc xưởng đã nhập.");
    addResult(brief,"Ý nghĩa nghiệp vụ","Bước tra cứu quan hệ đã chạy và chưa tạo cờ. Các cờ ảnh, chứng từ hoặc XGBoost vẫn được xem độc lập.");
    addResult(brief,"Giới hạn","Hồ sơ ngoài kho hiện tại chưa được đối chiếu; kết quả này không chứng minh hồ sơ không có liên quan ở nơi khác.");
  }
}

async function renderEvents() {
  const list=$("eventsList");list.replaceChildren();
  const intro=$("auditIntro");intro.replaceChildren();
  if(analysis){
    addResult(intro,"Lượt phân tích của hệ thống",`${new Date(analysis.created_at).toLocaleString("vi-VN")} · mã truy vết ${analysis.trace_id.slice(0,12)}… · trạng thái ${analysis.analysis_status}.`);
    addResult(intro,"Nhật ký này dùng để làm gì","Lưu quyết định và chỉnh sửa của con người để quản lý có thể kiểm tra ai đã xử lý, căn cứ nào được dùng và kết quả model nào đang được tham chiếu.");
  }
  try {
    const events=await api.getEvents(claimId);
    if (!events.length) {const empty=document.createElement("div");empty.className="empty";empty.textContent="Chưa có thao tác của người duyệt. Chọn quyết định ở cột bên phải hoặc sửa một trường chứng từ, rồi bấm Lưu; bản ghi sẽ xuất hiện tại đây.";list.append(empty);return;}
    events.slice().reverse().forEach(row=>{
      const item=document.createElement("article");item.className="event";const time=document.createElement("time");time.textContent=new Date(row.created_at).toLocaleString("vi-VN");const title=document.createElement("strong");const note=document.createElement("p");
      if(row.event_type==="review"){title.textContent=`Quyết định: ${{continue_processing:"Tiếp tục xử lý",request_evidence:"Yêu cầu bổ sung",special_review:"Rà soát chuyên sâu"}[row.decision]||row.decision}`;note.textContent=`Người thực hiện: ${row.reviewer_id} · Lý do: ${row.reason}`}
      else{title.textContent=`Sửa trường: ${{total_amount:"Tổng tiền",document_date:"Ngày chứng từ",plate_number:"Biển số"}[row.field_name]||row.field_name}`;note.textContent=`${row.reviewer_id} sửa “${row.original_value??"chưa có"}” thành “${row.corrected_value}” · Lý do: ${row.reason}`}
      const trace=document.createElement("small");trace.textContent=`Mã phân tích: ${String(row.trace_id||"").slice(0,12)}…`;item.append(time,title,note,trace);list.append(item);
    });
  } catch(error) {const empty=document.createElement("div");empty.className="empty";empty.textContent=`Không tải được nhật ký: ${error.message}`;list.append(empty);}
}

function render(a,health) {
  analysis=a;claimId=a.claim_id;$("crumbId").textContent=claimId;$("heroId").textContent=claimId;
  $("modeBadge").textContent=health.mode==="live"?"API live · research v1":"API fixture · prototype";
  $("sideMode").textContent=`${health.mode.toUpperCase()} · ${health.product_version}`;
  $("demoBanner").hidden=!claimId.startsWith("CLM-DEMO-SYN");
  const riskStatus=a.module_status?.tabular_risk||{};
  $("priorityValue").textContent=a.research_risk_score==null?"Không đủ dữ liệu":`${(a.research_risk_score*100).toFixed(1)}/100`;
  $("analysisValue").textContent=a.research_risk_score==null
    ? `${riskStatus.missing_field_count?`Thiếu ${riskStatus.missing_field_count} trường nghiệp vụ. `:""}Ảnh, chứng từ và quan hệ vẫn được kiểm tra.`
    : "Dùng xếp thứ tự xem hồ sơ; không phải xác suất gian lận";
  $("scoreValue").textContent=a.research_risk_score==null?"Chưa chấm":`${(a.research_risk_score*100).toFixed(1)} / 100`;
  $("riskStat").classList.toggle("missing",a.research_risk_score==null);
  let required=a.required_evidence_count||0,present=a.present_required_count||0;
  if(!required){
    const presentKinds=new Set((a.evidence||[]).map(item=>item.kind).filter(kind=>["claim","image","document"].includes(kind))).size;
    required=presentKinds+(a.missing_evidence?.length||0);
    present=presentKinds;
  }
  $("evidenceValue").textContent=required?`${present}/${required} loại`:`${Math.round(a.evidence_completeness*100)}%`;
  const missingLabels=(a.missing_evidence||[]).map(evidenceTypeName);
  $("missingValue").textContent=missingLabels.length?`Cần bổ sung: ${missingLabels.join("; ")}`:"Đã nhận đủ nhóm hồ sơ yêu cầu; vẫn cần kiểm tra nội dung";
  $("evidenceStat").classList.toggle("warning",missingLabels.length>0);
  const highCount=a.signals.filter(signal=>signal.severity==="high").length,reviewCount=a.signals.filter(signal=>signal.severity==="review").length;
  const flagCount=highCount+reviewCount;
  $("signalValue").textContent=flagCount?`⚑ ${formatNumber(flagCount)} cờ`:"✓ 0 cờ";
  $("signalBreakdown").textContent=flagCount?`${highCount} mức cao · ${reviewCount} cần rà soát · mở thẻ có cờ để xem căn cứ`:"Chưa phát hiện điểm cần rà soát trong phần đã chạy; không phải bảo đảm hồ sơ an toàn";
  $("signalStat").classList.toggle("alert",highCount>0);
  $("signalStat").classList.toggle("warning",highCount===0&&reviewCount>0);
  $("signalStat").classList.toggle("clear",flagCount===0);
  const evidenceFlagCount=a.signals.filter(signal=>signal.severity!=="info"&&["document","consistency","damage","authenticity"].includes(signal.category)).length;
  const relationFlagCount=a.signals.filter(signal=>signal.severity!=="info"&&signal.category==="relationship").length;
  [["overviewTabCount",flagCount],["evidenceTabCount",evidenceFlagCount],["relationTabCount",relationFlagCount]].forEach(([id,count])=>{const badge=$(id);badge.hidden=!count;badge.textContent=count?`⚑ ${count}`:"";badge.classList.toggle("high",id==="overviewTabCount"&&highCount>0)});
  $("heroSubtitle").textContent=a.analysis_status==="partial"?"Hệ thống đã phân tích phần có thể và chỉ rõ phần chưa kiểm tra; thiếu module không được hiểu là hồ sơ bình thường.":"Mở từng tín hiệu để xem bằng chứng, ý nghĩa và hành động trước khi quyết định.";
  renderBusiness(a);renderModules(a);renderScoreDetails(a);renderSignals(a);renderEvidence(a);renderGraph(a);renderEvents();
  const requestedTab=new URLSearchParams(location.search).get("tab") || location.hash.slice(1);
  if(["overview","evidence","relations","audit"].includes(requestedTab)) {
    openTab(requestedTab);
  }
}

async function runAnalysisJob(id,{force=false}={}) {
  let job=await api.startAnalysisJob(id,{force_recompute:force});
  while(["queued","running"].includes(job.status)){
    $("refreshButton").textContent=`Đang phân tích · ${Math.floor(job.elapsed_seconds||0)}s`;
    await new Promise(resolve=>setTimeout(resolve,1000));
    job=await api.getAnalysisJob(id,job.job_id);
  }
  if(job.status==="failed")throw new Error(job.error||"Job phân tích gặp lỗi.");
  return api.getAnalysis(id);
}

async function load() {
  setError("");$("refreshButton").disabled=true;
  try {
    const health=await api.health();
    const requested=new URLSearchParams(location.search).get("claim_id");
    const id=requested||(health.mode==="live"?"CLM-DEMO-SYN-001":"CLM-2026-00418");
    let result;
    try {result=await api.getAnalysis(id);}
    catch(error) {
      if(!(error instanceof ClaimApiError)||error.status!==404)throw error;
      result=await runAnalysisJob(id);
    }
    render(result,health);
  } catch(error) {
    const detail=error instanceof ClaimApiError&&error.status===404?"Hồ sơ demo chưa được nạp. Chạy scripts/seed_synthetic_demo.py, rồi tải lại trang.":error.message;
    setError(`Không mở được hồ sơ: ${detail}`);
  } finally {$("refreshButton").disabled=false;$("refreshButton").textContent="↻ Phân tích lại";}
}

$("refreshButton").addEventListener("click",async()=>{
  setError("");$("refreshButton").disabled=true;
  try {const health=await api.health();const result=await runAnalysisJob(claimId,{force:true});render(result,health);}
  catch(error){setError(`Không phân tích lại được hồ sơ: ${error.message}`);}
  finally{$("refreshButton").disabled=false;$("refreshButton").textContent="↻ Phân tích lại";}
});
$("reloadEvents").addEventListener("click",renderEvents);
$("fieldName").addEventListener("change",refreshCorrectionContext);
$("saveReview").addEventListener("click",async()=>{
  const selected=document.querySelector('input[name="decision"]:checked');const reason=$("reviewReason").value.trim();const feedback=$("reviewFeedback");feedback.className="feedback";
  if(!selected||reason.split(/\s+/).length<3){feedback.textContent="Chọn hướng xử lý và ghi lý do ít nhất ba từ.";feedback.classList.add("error");return;}
  try {await api.saveReview(claimId,{reviewer_id:"demo-reviewer",decision:selected.value,reason});feedback.textContent="Đã lưu quyết định. Đang mở tab Nhật ký; Dashboard quản lý cũng sẽ hiển thị quyết định này.";await renderEvents();openTab("audit");}
  catch(error){feedback.textContent=`Chưa lưu được: ${error.message}`;feedback.classList.add("error");}
});
$("saveCorrection").addEventListener("click",async()=>{
  const field=$("fieldName").value, corrected=$("correctedValue").value.trim(),reason=$("correctionReason").value.trim(),feedback=$("correctionFeedback");feedback.className="feedback";
  if(!corrected||reason.split(/\s+/).length<3){feedback.textContent="Nhập giá trị đúng và lý do ít nhất ba từ.";feedback.classList.add("error");return;}
  const documentId=analysis?.extracted_fields?.document_results?.[0]?.document_id || analysis?.evidence?.find(item=>item.kind==="document")?.evidence_id || "document-unidentified";
  try {await api.saveCorrection(claimId,{reviewer_id:"demo-reviewer",document_id:documentId,field_name:field,original_value:currentFieldValue(field),corrected_value:corrected,reason});feedback.textContent="Đã lưu chỉnh sửa vào nhật ký. Mở tab Nhật ký để xem bản ghi vừa tạo.";$("correctedValue").value="";$("correctionReason").value="";renderEvents();}
  catch(error){feedback.textContent=`Chưa lưu được: ${error.message}`;feedback.classList.add("error");}
});

load();
