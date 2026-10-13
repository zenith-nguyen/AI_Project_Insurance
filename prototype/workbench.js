import {ClaimReviewClient, ClaimApiError} from "/api-client.js";

const api = new ClaimReviewClient();
const $ = (id) => document.getElementById(id);
const statusNames = {completed:"Đã chạy",completed_precomputed:"Trường chuẩn bị sẵn",unavailable:"Chưa kích hoạt",skipped_missing_input:"Thiếu đầu vào",blocked_missing_input:"Thiếu dữ liệu bảng",error:"Gặp lỗi",skipped_optional:"Không yêu cầu",partial:"Chưa đầy đủ"};
const moduleNames = {tabular_risk:"Xếp hạng hồ sơ",document_pipeline:"Đọc chứng từ",damage_segmentation:"Ảnh hư hỏng",media_authenticity:"Nguồn gốc ảnh",consistency:"Đối chiếu thông tin",relationships:"Quan hệ hồ sơ",guided_capture:"Ảnh chụp hướng dẫn"};
const categoryNames = {risk:"Điểm ưu tiên",damage:"Ảnh xe",document:"Chứng từ",consistency:"Đối chiếu",relationship:"Quan hệ",authenticity:"Nguồn gốc ảnh"};
const priorityNames = {normal:"Thông thường",review:"Cần rà soát",high:"Ưu tiên cao"};
const analysisNames = {complete:"Đủ module",partial:"Phân tích một phần",blocked:"Chưa chấm được"};
const formatNumber = (value) => value == null ? "—" : new Intl.NumberFormat("vi-VN").format(value);
let claimId = "";
let analysis = null;

function setError(message) { const box=$("errorBox"); box.textContent=message; box.hidden=!message; }
function openTab(name) {
  document.querySelectorAll(".tabs button").forEach(button=>button.classList.toggle("active",button.dataset.tab===name));
  document.querySelectorAll(".panel").forEach(panel=>panel.classList.toggle("active",panel.id===name));
}
document.querySelectorAll(".tabs button").forEach(button=>button.addEventListener("click",()=>openTab(button.dataset.tab)));

function renderModules(a) {
  const entries = Object.entries(a.module_status || {});
  $("moduleSummary").textContent = `${entries.filter(([,x])=>x.status==="completed").length}/${entries.length} module đã chạy`;
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
  if(value.status==="blocked_missing_input") return "Thiếu trường dữ liệu cần để chấm điểm.";
  return status;
}

function renderSignals(a) {
  const list=$("signals"); list.replaceChildren();
  if (!a.signals.length) { const empty=document.createElement("div");empty.className="empty";empty.textContent="Chưa có tín hiệu được ghi nhận. Hãy vẫn xem ảnh và chứng từ gốc.";list.append(empty);return; }
  a.signals.forEach(signal=>{
    const card=document.createElement("article");card.className=`signal ${signal.severity}`;
    const category=document.createElement("div");category.className="category";category.textContent=categoryNames[signal.category]||signal.category;
    const title=document.createElement("h3");title.textContent=signal.title;
    const note=document.createElement("p");note.textContent=signal.category==="consistency"&&signal.explanation.includes("amount_mismatch")?"Số tiền trên chứng từ khác số tiền khai báo; cần xem bản gốc và xác nhận lại.":signal.explanation;
    const button=document.createElement("button");button.type="button";button.textContent="Xem phần liên quan →";
    const tab=signal.category==="relationship"?"relations":["document","consistency","damage","authenticity"].includes(signal.category)?"evidence":"overview";
    button.addEventListener("click",()=>openTab(tab));card.append(category,title,note,button);list.append(card);
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
      if (kind==="damage" && item.mask_polygon?.length) {
        shape=document.createElementNS("http://www.w3.org/2000/svg","polygon");
        shape.setAttribute("points",item.mask_polygon.map(point=>point.join(",")).join(" "));
      } else {
        const box=kind==="damage"?item.box_xyxy:item.bbox && [item.bbox.x1,item.bbox.y1,item.bbox.x2,item.bbox.y2];
        if (!box || box.length!==4) continue;
        shape=document.createElementNS("http://www.w3.org/2000/svg","rect");
        shape.setAttribute("x",box[0]);shape.setAttribute("y",box[1]);shape.setAttribute("width",box[2]-box[0]);shape.setAttribute("height",box[3]-box[1]);
      }
      shape.setAttribute("fill",kind==="damage"?"#17b99b55":"#d6a34333");shape.setAttribute("stroke",kind==="damage"?"#16a88c":"#bb8531");shape.setAttribute("stroke-width","3");
      shape.setAttribute("vector-effect","non-scaling-stroke");svg.append(shape);
    }
    container.append(svg);
  },{once:true});
}

function renderEvidence(a) {
  const images=a.evidence.filter(e=>e.kind==="image" && e.source_uri?.startsWith("runtime://"));
  const documents=a.evidence.filter(e=>e.kind==="document" && e.source_uri?.startsWith("runtime://"));
  const detections=a.extracted_fields?.damage_detections||[];
  const docResults=a.extracted_fields?.document_results||[];
  const authenticity=a.extracted_fields?.media_authenticity||[];
  const vehicle=$("vehiclePreview");vehicle.replaceChildren();
  if (images.length) {
    const img=document.createElement("img");img.alt="Ảnh xe đã nộp cho hồ sơ";img.src=api.evidenceContentUrl(a.claim_id,images[0].evidence_id);
    vehicle.append(img);addOverlay(vehicle,img,detections.filter(d=>d.evidence_id===images[0].evidence_id),"damage");
    $("vehicleMeta").textContent=`${images.length} ảnh · ${images[0].label}`;
  } else {vehicle.textContent="Hồ sơ này chưa có ảnh xe.";$("vehicleMeta").textContent="Không suy ra xe không hư hỏng khi thiếu ảnh.";}
  const damageList=$("damageResults");damageList.replaceChildren();
  const damageText=detections.length?`${detections.length} vùng hư hỏng do YOLO đánh dấu: ${detections.map(x=>x.class_name).join(", ")}`:"Chưa có kết quả YOLO trên ảnh này.";
  addResult(damageList,"Hư hỏng",damageText);
  addResult(damageList,"Nguồn gốc ảnh",authenticity.length?`Trạng thái ${authenticity[0].verdict}. Metadata không đủ để chứng minh ảnh thật hay giả.`:"Chưa phân tích nguồn gốc ảnh.");
  const preview=$("documentPreview");preview.replaceChildren();
  if (documents.length) {
    const evidence=documents[0];const url=api.evidenceContentUrl(a.claim_id,evidence.evidence_id);
    if (evidence.label.toLowerCase().endsWith(".pdf")) {const frame=document.createElement("iframe");frame.src=url;frame.title="Chứng từ gốc";preview.append(frame);}
    else {const img=document.createElement("img");img.src=url;img.alt="Chứng từ gốc đã nộp";preview.append(img);const result=docResults.find(row=>row.document_id===evidence.evidence_id);addOverlay(preview,img,(result?.fields||[]).filter(field=>field.page_number===1),"document");}
    $("documentMeta").textContent=`${documents.length} tệp · ${evidence.label}`;
  } else {preview.textContent="Hồ sơ này chưa có chứng từ nhị phân.";$("documentMeta").textContent="Có thể vẫn có trường demo chuẩn bị sẵn.";}
  const fields=$("documentResults");fields.replaceChildren();
  if (docResults.length) {
    docResults.flatMap(row=>row.fields||[]).forEach(field=>addResult(fields,field.field_name,String(field.normalized_value)));
  } else if (a.module_status?.document_pipeline?.status==="completed_precomputed") {
    addResult(fields,"Trường demo chuẩn bị sẵn",`Tổng tiền: ${formatNumber(a.extracted_fields?.total_amount)} · Ngày: ${a.extracted_fields?.document_date||"—"}. Đây không phải output OCR/KIE của tệp vừa tải.`);
  } else {addResult(fields,"Trích xuất",a.module_status?.document_pipeline?.reason||"Chưa có kết quả đọc chứng từ.");}
}

function addResult(parent,title,detail){const item=document.createElement("div");item.className="result-item";const head=document.createElement("b");head.textContent=title;const body=document.createElement("span");body.textContent=detail;item.append(head,body);parent.append(item);}

function renderGraph(a) {
  const graph=a.graph_features||{}, box=$("graphMetrics");box.replaceChildren();
  if(graph.data_status==="not_provided") {$("graphState").textContent="Chưa có dữ liệu quan hệ. Điều này không đồng nghĩa không có liên kết đáng chú ý.";return;}
  $("graphState").textContent="Chỉ tính những liên kết đã có trước thời điểm chấm hồ sơ.";
  [["shared_entity_count","Thực thể dùng chung"],["two_hop_claim_count","Hồ sơ trong 2 bước liên kết"],["connected_component_size","Quy mô cụm liên kết"],["graph_degree","Số liên kết trực tiếp"]].forEach(([key,label])=>{
    const tile=document.createElement("div");tile.className="graph-metric";const number=document.createElement("strong");number.textContent=formatNumber(graph[key]);const name=document.createElement("span");name.textContent=label;tile.append(number,name);box.append(tile);
  });
}

async function renderEvents() {
  const list=$("eventsList");list.replaceChildren();
  try {
    const events=await api.getEvents(claimId);
    if (!events.length) {const empty=document.createElement("div");empty.className="empty";empty.textContent="Chưa có quyết định hoặc chỉnh sửa nào được lưu cho hồ sơ này.";list.append(empty);return;}
    events.slice().reverse().forEach(row=>{
      const item=document.createElement("article");item.className="event";const time=document.createElement("time");time.textContent=new Date(row.created_at).toLocaleString("vi-VN");const title=document.createElement("strong");title.textContent=row.event_type==="review"?"Quyết định của người duyệt":"Chỉnh sửa trường chứng từ";const note=document.createElement("p");note.textContent=row.event_type==="review"?`${row.reviewer_id} · ${row.decision} · ${row.reason}`:`${row.reviewer_id} · ${row.field_name}: ${row.original_value} → ${row.corrected_value} · ${row.reason}`;item.append(time,title,note);list.append(item);
    });
  } catch(error) {const empty=document.createElement("div");empty.className="empty";empty.textContent=`Không tải được nhật ký: ${error.message}`;list.append(empty);}
}

function render(a,health) {
  analysis=a;claimId=a.claim_id;$("crumbId").textContent=claimId;$("heroId").textContent=claimId;
  $("modeBadge").textContent=health.mode==="live"?"API live · research v1":"API fixture · prototype";
  $("sideMode").textContent=`${health.mode.toUpperCase()} · ${health.product_version}`;
  $("demoBanner").hidden=!claimId.startsWith("CLM-DEMO-SYN");
  $("priorityValue").textContent=priorityNames[a.priority]||a.priority;
  $("analysisValue").textContent=analysisNames[a.analysis_status]||a.analysis_status;
  $("scoreValue").textContent=a.research_risk_score==null?"Chưa chấm":`${(a.research_risk_score*100).toFixed(1)} / 100`;
  $("evidenceValue").textContent=`${Math.round(a.evidence_completeness*100)}%`;
  $("missingValue").textContent=a.missing_evidence.length?`Thiếu ${a.missing_evidence.length} loại bằng chứng`:"Đã đủ loại bằng chứng yêu cầu";
  $("signalValue").textContent=formatNumber(a.signals.length);
  $("heroSubtitle").textContent=a.analysis_status==="partial"?"Một số module chưa chạy; điểm xếp hạng và bằng chứng đã có vẫn hiển thị rõ.":"Mở từng tín hiệu để xem bằng chứng liên quan trước khi quyết định.";
  renderModules(a);renderSignals(a);renderEvidence(a);renderGraph(a);renderEvents();
  const requestedTab=new URLSearchParams(location.search).get("tab") || location.hash.slice(1);
  if(["overview","evidence","relations","audit"].includes(requestedTab)) {
    openTab(requestedTab);
  }
}

async function load() {
  setError("");$("refreshButton").disabled=true;
  try {
    const health=await api.health();
    const requested=new URLSearchParams(location.search).get("claim_id");
    const id=requested||(health.mode==="live"?"CLM-DEMO-SYN-001":"CLM-2026-00418");
    const result=await api.analyzeClaim(id);
    render(result,health);
  } catch(error) {
    const detail=error instanceof ClaimApiError&&error.status===404?"Hồ sơ demo chưa được nạp. Chạy scripts/seed_synthetic_demo.py, rồi tải lại trang.":error.message;
    setError(`Không mở được hồ sơ: ${detail}`);
  } finally {$("refreshButton").disabled=false;}
}

$("refreshButton").addEventListener("click",load);
$("reloadEvents").addEventListener("click",renderEvents);
$("saveReview").addEventListener("click",async()=>{
  const selected=document.querySelector('input[name="decision"]:checked');const reason=$("reviewReason").value.trim();const feedback=$("reviewFeedback");feedback.className="feedback";
  if(!selected||reason.split(/\s+/).length<3){feedback.textContent="Chọn hướng xử lý và ghi lý do ít nhất ba từ.";feedback.classList.add("error");return;}
  try {await api.saveReview(claimId,{reviewer_id:"demo-reviewer",decision:selected.value,reason});feedback.textContent="Đã lưu quyết định vào nhật ký; người duyệt vẫn chịu trách nhiệm xác minh.";renderEvents();}
  catch(error){feedback.textContent=`Chưa lưu được: ${error.message}`;feedback.classList.add("error");}
});
$("saveCorrection").addEventListener("click",async()=>{
  const field=$("fieldName").value, corrected=$("correctedValue").value.trim(),reason=$("correctionReason").value.trim(),feedback=$("correctionFeedback");feedback.className="feedback";
  if(!corrected||reason.split(/\s+/).length<3){feedback.textContent="Nhập giá trị đúng và lý do ít nhất ba từ.";feedback.classList.add("error");return;}
  const documentId=analysis?.extracted_fields?.document_results?.[0]?.document_id || analysis?.evidence?.find(item=>item.kind==="document")?.evidence_id || "document-unidentified";
  try {await api.saveCorrection(claimId,{reviewer_id:"demo-reviewer",document_id:documentId,field_name:field,original_value:analysis?.extracted_fields?.[field]??null,corrected_value:corrected,reason});feedback.textContent="Đã lưu chỉnh sửa vào nhật ký. Kết quả model không tự thay đổi; cần chạy quy trình xử lý lại theo nghiệp vụ.";renderEvents();}
  catch(error){feedback.textContent=`Chưa lưu được: ${error.message}`;feedback.classList.add("error");}
});

load();
