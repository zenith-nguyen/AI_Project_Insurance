import {ClaimReviewClient} from "/api-client.js";

const api=new ClaimReviewClient();
const $=id=>document.getElementById(id);
const priorityNames={high:"Ưu tiên cao",review:"Cần rà soát",normal:"Thông thường",unscored:"Chưa phân tích"};
const decisionNames={continue_processing:"Tiếp tục xử lý",request_evidence:"Yêu cầu bổ sung",special_review:"Rà soát chuyên sâu"};
const modelNames={tabular_risk:"XGBoost · xếp hạng hồ sơ",damage_segmentation:"YOLOv8s-seg · hư hỏng",document_classifier:"DiT · loại chứng từ",document_ocr:"PaddleOCR · đọc chữ",ocr:"PaddleOCR · đọc chữ",document_kie:"LayoutLMv3 · trích trường",consistency_rules:"Rules · đối chiếu",consistency:"Rules · đối chiếu",relationships:"NetworkX · quan hệ",media_authenticity:"Media authenticity · nguồn gốc ảnh"};
let claims=[];

const formatDate=value=>value?new Date(value).toLocaleString("vi-VN"):"—";
function setError(message){$("errorBox").textContent=message;$("errorBox").hidden=!message;}
function stat(){
  $("totalClaims").textContent=claims.length;
  $("highClaims").textContent=claims.filter(row=>row.priority==="high").length;
  $("unscoredClaims").textContent=claims.filter(row=>!row.risk_score_available).length;
  $("reviewedClaims").textContent=claims.filter(row=>row.latest_decision).length;
}
function badge(text,type="normal"){const span=document.createElement("span");span.className=`queue-badge ${type}`;span.textContent=text;return span;}
function renderQueue(){
  const search=$("search").value.trim().toLowerCase(),status=$("statusFilter").value,priority=$("priorityFilter").value,decision=$("decisionFilter").value;
  const filtered=claims.filter(row=>(!search||`${row.claim_id} ${row.plate_number||""}`.toLowerCase().includes(search))&&(status==="all"||(status==="analyzed"?row.analysis_status!=="not_analyzed":row.analysis_status==="not_analyzed"))&&(priority==="all"||row.priority===priority)&&(decision==="all"||(decision==="none"?!row.latest_decision:row.latest_decision===decision)));
  $("queueCount").textContent=`Hiển thị ${filtered.length}/${claims.length} hồ sơ`;
  const body=$("claimRows");body.replaceChildren();$("queueEmpty").hidden=filtered.length>0;
  filtered.forEach(row=>{
    const tr=document.createElement("tr");
    const identity=document.createElement("td");const id=document.createElement("a");id.className="claim-link";id.href=`/?claim_id=${encodeURIComponent(row.claim_id)}`;id.textContent=row.claim_id;const time=document.createElement("small");time.textContent=`${row.plate_number||"Chưa có biển số"} · ${formatDate(row.created_at)}`;identity.append(id,time);
    const reason=document.createElement("td");reason.append(badge(priorityNames[row.priority]||row.priority,row.priority));const reasonText=document.createElement("small");reasonText.textContent=row.priority_reason;reason.append(reasonText);
    const score=document.createElement("td");score.textContent=row.risk_score_available?`${(row.research_risk_score*100).toFixed(1)}/100`:"Chưa chấm";const scoreNote=document.createElement("small");scoreNote.textContent=row.risk_score_available?"Điểm xếp hạng, không phải xác suất fraud":"Thiếu feature bảng";score.append(scoreNote);
    const evidence=document.createElement("td");evidence.textContent=`${row.present_required_count}/${row.required_evidence_count} loại`;const fileNote=document.createElement("small");fileNote.textContent=`${row.uploaded_file_count} file đã tải${row.missing_evidence.length?` · thiếu ${row.missing_evidence.length} loại`:""}`;evidence.append(fileNote);
    const signals=document.createElement("td");signals.textContent=`${row.signal_count} cờ`;const signalNote=document.createElement("small");signalNote.textContent=`${row.high_signal_count} high · ${row.review_signal_count} review`;signals.append(signalNote);
    const decisionCell=document.createElement("td");decisionCell.textContent=row.latest_decision?(decisionNames[row.latest_decision]||row.latest_decision):"Chưa có";const eventNote=document.createElement("small");eventNote.textContent=row.latest_decision?`${row.latest_reviewer} · ${formatDate(row.latest_event_at)}`:`${row.event_count} bản ghi audit`;decisionCell.append(eventNote);
    const actions=document.createElement("td");actions.className="queue-actions";const open=document.createElement("a");open.href=`/?claim_id=${encodeURIComponent(row.claim_id)}`;open.textContent="Mở";const history=document.createElement("a");history.href=`/?claim_id=${encodeURIComponent(row.claim_id)}&tab=audit`;history.textContent="Lịch sử";actions.append(open,history);
    tr.append(identity,reason,score,evidence,signals,decisionCell,actions);body.append(tr);
  });
}
function renderProof(proof){
  $("externalApiBadge").textContent=proof.external_llm_api_used?"Có API LLM ngoài":"Không dùng API LLM ngoài";
  $("processingLocation").textContent=proof.processing_location==="local_process"?"Checkpoint/rules chạy trong tiến trình local":proof.processing_location;
  $("externalData").textContent=proof.claim_data_sent_to_external_llm?"Có":"Không";
  $("claimStorage").textContent=proof.storage.claim_files;$("auditStorage").textContent=proof.storage.audit_log;
  const target=$("modelProof");target.replaceChildren();
  Object.entries(proof.models).forEach(([key,model])=>{const card=document.createElement("article");const title=document.createElement("h3");title.textContent=modelNames[key]||key;const origin=document.createElement("p");origin.textContent=model.training_origin;const facts=document.createElement("dl");[["Version",model.version],["Trạng thái",model.status],["Metric",`${model.metric}: ${model.metric_value}`],["Tập đánh giá",model.evaluation_split],["SHA-256",model.artifact_hash]].forEach(([name,value])=>{const dt=document.createElement("dt");dt.textContent=name;const dd=document.createElement("dd");dd.textContent=value;facts.append(dt,dd)});card.append(title,origin,facts);target.append(card)});
}
async function load(){
  setError("");$("reload").disabled=true;
  try{const [health,rows,proof]=await Promise.all([api.health(),api.listClaims(),api.modelEvidence()]);claims=rows;$("modeBadge").textContent=`${health.mode.toUpperCase()} · ${health.product_version}`;$("sideMode").textContent=`${health.mode.toUpperCase()} · ${health.product_version}`;stat();renderQueue();renderProof(proof)}catch(error){setError(`Không tải được dashboard: ${error.message}`)}finally{$("reload").disabled=false}
}
[$("search"),$("statusFilter"),$("priorityFilter"),$("decisionFilter")].forEach(element=>element.addEventListener("input",renderQueue));
$("reload").addEventListener("click",load);
load();
