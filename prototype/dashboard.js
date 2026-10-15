import {ClaimReviewClient} from "/api-client.js?v=20261015f";

const api=new ClaimReviewClient();
const $=id=>document.getElementById(id);
const priorityNames={high:"Ưu tiên cao",review:"Cần rà soát",normal:"Thông thường",unscored:"Chưa phân tích",analyzing:"Đang phân tích"};
const decisionNames={continue_processing:"Tiếp tục xử lý",request_evidence:"Yêu cầu bổ sung",special_review:"Rà soát chuyên sâu"};
const modelNames={tabular_risk:"XGBoost · xếp hạng hồ sơ",damage_segmentation:"YOLOv8s-seg · hư hỏng",document_classifier:"DiT · loại chứng từ",document_ocr:"PaddleOCR · đọc chữ",ocr:"PaddleOCR · đọc chữ",document_kie:"LayoutLMv3 · trích trường",consistency_rules:"Rules · đối chiếu",consistency:"Rules · đối chiếu",relationships:"NetworkX · quan hệ",media_authenticity:"Media authenticity · nguồn gốc ảnh"};
const modelStatus={research_validated:"Đã đánh giá nghiên cứu",final_test_complete:"Đã hoàn tất final test",baseline_needs_improvement:"Baseline cần cải thiện",demo_only:"Demo kỹ thuật",engineering_v1_needs_domain_validation:"Cần validation đúng miền"};
const improvementStatusNames={complete_engineering:"Đã xong phần kỹ thuật",in_progress:"Đang triển khai/đánh giá",waiting_for_domain_data:"Chờ dữ liệu đúng miền"};
const modelBusiness={
  tabular_risk:{value:"Đưa hồ sơ có tín hiệu mạnh lên trước để sử dụng thời gian của giám định viên hiệu quả hơn.",limit:"Recall@10% test mới 22,4%; điểm không phải xác suất gian lận.",next:"Bổ sung feature S1–S5 đúng thời điểm, dữ liệu nhãn đáng tin hơn và đánh giá Net Value."},
  damage_segmentation:{value:"Khoanh vùng hư hỏng để người duyệt nhìn nhanh vị trí cần đối chiếu với mô tả và báo giá.",limit:"mAP trung bình; sáu lớp CarDD không bao phủ mọi hư hỏng và chưa phải dữ liệu Việt Nam.",next:"Lập error gallery, bổ sung ảnh đúng miền cho crack/dent/scratch và đánh giá theo loại xe, góc chụp."},
  document_classifier:{value:"Tự nhận biết loại chứng từ để chuyển đúng luồng OCR/KIE, giảm thao tác phân loại thủ công.",limit:"Đánh giá trên RVL-CDIP; loại giấy tờ bảo hiểm Việt Nam có thể khác.",next:"Tạo taxonomy chứng từ nghiệp vụ và validation set tiếng Việt đã ẩn danh."},
  ocr:{value:"Biến chữ trên chứng từ thành dữ liệu có thể tìm kiếm, đối chiếu và sửa có nhật ký.",limit:"CER 40,97% còn cao; chưa nên tự dùng số tiền/ngày mà không xác nhận.",next:"Error analysis ảnh xoay, mờ và chữ nhỏ; deskew, orientation, OCR tiếng Việt và benchmark lại validation."},
  document_kie:{value:"Trích ngày và tổng tiền để so sánh tự động với thông tin claim.",limit:"Huấn luyện trên hóa đơn SROIE; biên bản tai nạn tiếng Việt ngoài miền đánh giá.",next:"Gắn nhãn chứng từ bảo hiểm Việt Nam, mở rộng field schema và chỉ tối ưu trên validation/dữ liệu mới."},
  consistency:{value:"Chỉ ra số tiền, ngày hoặc biển số không khớp giữa khai báo và chứng từ.",limit:"Luật demo chưa được nghiệp vụ phê duyệt và có thể tạo cảnh báo giả.",next:"Version hóa rule, thêm tolerance theo nghiệp vụ và đo precision trên golden claims."},
  relationships:{value:"Tìm hồ sơ dùng chung số điện thoại, biển số hoặc xưởng để mở rộng phạm vi điều tra.",limit:"Thiếu entity thật hoặc timestamp thì không thể kết luận không có quan hệ.",next:"Chuẩn hóa entity resolution, temporal edges và đánh giá case điều tra đã xác minh."},
  media_authenticity:{value:"Tìm dấu nguồn gốc, chỉnh sửa và ảnh bị tái sử dụng để yêu cầu bằng chứng tốt hơn.",limit:"Không phải universal AI detector; ảnh mất marker có thể chỉ trả kết quả chưa xác định.",next:"Benchmark camera/edit/social/re-capture/AI đúng miền; chỉ bật pixel model sau calibration và threshold gate."}
};
let claims=[];

const formatDate=value=>value?new Date(value).toLocaleString("vi-VN"):"—";
function setError(message){$("errorBox").textContent=message;$("errorBox").hidden=!message;}
function stat(){
  $("totalClaims").textContent=claims.filter(row=>!["not_analyzed","analyzing"].includes(row.analysis_status)).length;
  $("highClaims").textContent=claims.filter(row=>row.priority==="high").length;
  $("unscoredClaims").textContent=claims.filter(row=>row.analysis_status==="not_analyzed").length;
  $("reviewedClaims").textContent=claims.filter(row=>row.latest_decision).length;
  $("runningClaims").textContent=claims.filter(row=>row.analysis_status==="analyzing").length;
}
function badge(text,type="normal"){const span=document.createElement("span");span.className=`queue-badge ${type}`;span.textContent=text;return span;}
function renderQueue(){
  const search=$("search").value.trim().toLowerCase(),status=$("statusFilter").value,priority=$("priorityFilter").value,decision=$("decisionFilter").value;
  const filtered=claims.filter(row=>(!search||`${row.claim_id} ${row.plate_number||""}`.toLowerCase().includes(search))&&(status==="all"||(status==="analyzed"?row.analysis_status!=="not_analyzed":row.analysis_status==="not_analyzed"))&&(priority==="all"||row.priority===priority)&&(decision==="all"||(decision==="none"?!row.latest_decision:row.latest_decision===decision)));
  $("queueCount").textContent=`Hiển thị ${filtered.length}/${claims.length} hồ sơ`;
  const body=$("claimRows");body.replaceChildren();$("queueEmpty").hidden=filtered.length>0;
  filtered.forEach(row=>{
    const tr=document.createElement("tr");
    const identity=document.createElement("td");const id=document.createElement("a");id.className="claim-link";id.href=`/?view=workbench&claim_id=${encodeURIComponent(row.claim_id)}`;id.textContent=row.claim_id;const time=document.createElement("small");time.textContent=`${row.plate_number||"Chưa có biển số"} · ${formatDate(row.created_at)}`;identity.append(id,time);
    const reason=document.createElement("td");reason.append(badge(priorityNames[row.priority]||row.priority,row.priority));const reasonText=document.createElement("small");reasonText.textContent=row.priority_reason;reason.append(reasonText);
    const score=document.createElement("td");score.textContent=row.analysis_status==="analyzing"?"Đang chạy…":row.risk_score_available?`${(row.research_risk_score*100).toFixed(1)}/100`:"Chưa chấm";const scoreNote=document.createElement("small");scoreNote.textContent=row.analysis_status==="analyzing"?(row.job_message||"Model đang xử lý nền"):row.risk_score_available?"Điểm xếp hạng, không phải xác suất fraud":"Thiếu feature bảng";score.append(scoreNote);
    const evidence=document.createElement("td");evidence.textContent=`${row.present_required_count}/${row.required_evidence_count} loại`;const fileNote=document.createElement("small");fileNote.textContent=`${row.uploaded_file_count} file đã tải${row.missing_evidence.length?` · thiếu ${row.missing_evidence.length} loại`:""}`;evidence.append(fileNote);
    const signals=document.createElement("td");signals.textContent=`${row.signal_count} cờ`;const signalNote=document.createElement("small");signalNote.textContent=`${row.high_signal_count} high · ${row.review_signal_count} review`;signals.append(signalNote);
    const decisionCell=document.createElement("td");decisionCell.textContent=row.latest_decision?(decisionNames[row.latest_decision]||row.latest_decision):"Chưa có";const eventNote=document.createElement("small");eventNote.textContent=row.latest_decision?`${row.latest_reviewer} · ${formatDate(row.latest_event_at)}`:`${row.event_count} bản ghi audit`;decisionCell.append(eventNote);
    const actions=document.createElement("td");actions.className="queue-actions";const open=document.createElement("a");open.href=`/?view=workbench&claim_id=${encodeURIComponent(row.claim_id)}`;open.textContent="Mở";const history=document.createElement("a");history.href=`/?view=workbench&claim_id=${encodeURIComponent(row.claim_id)}&tab=audit`;history.textContent="Lịch sử";actions.append(open,history);
    tr.append(identity,reason,score,evidence,signals,decisionCell,actions);body.append(tr);
  });
}
function renderProof(proof){
  $("externalApiBadge").textContent=proof.external_llm_api_used?"Có API LLM ngoài":"Không dùng API LLM ngoài";
  $("processingLocation").textContent=proof.processing_location==="local_process"?"Checkpoint/rules chạy trong tiến trình local":proof.processing_location;
  $("externalData").textContent=proof.claim_data_sent_to_external_llm?"Có":"Không";
  $("claimStorage").textContent=proof.storage.claim_files;$("auditStorage").textContent=proof.storage.audit_log;
  const target=$("modelProof");target.replaceChildren();
  Object.entries(proof.models).forEach(([key,model])=>{const card=document.createElement("article");const title=document.createElement("h3");title.textContent=modelNames[key]||key;const status=document.createElement("span");status.className="model-status";status.textContent=modelStatus[model.status]||model.status;const origin=document.createElement("p");origin.className="model-origin";origin.textContent=model.training_origin;const business=modelBusiness[key]||{value:"Module hỗ trợ tổng hợp bằng chứng cho người duyệt.",limit:"Cần đọc báo cáo đánh giá trước khi dùng.",next:"Bổ sung validation đúng miền nghiệp vụ."};const businessList=document.createElement("div");businessList.className="model-business";[["Giúp được gì?",business.value],["Giới hạn hiện tại",business.limit],["Kế hoạch nâng cấp",business.next]].forEach(([label,value])=>{const row=document.createElement("div");const b=document.createElement("b");b.textContent=label;const p=document.createElement("p");p.textContent=value;row.append(b,p);businessList.append(row)});const details=document.createElement("details");details.className="model-technical";const summary=document.createElement("summary");summary.textContent="Version, metric và checkpoint";const facts=document.createElement("dl");[["Version",model.version],["Trạng thái",modelStatus[model.status]||model.status],["Metric",`${model.metric}: ${model.metric_value}`],["Tập đánh giá",model.evaluation_split],["SHA-256",model.artifact_hash]].forEach(([name,value])=>{const dt=document.createElement("dt");dt.textContent=name;const dd=document.createElement("dd");dd.textContent=value;facts.append(dt,dd)});details.append(summary,facts);card.append(title,status,origin,businessList,details);target.append(card)});
}
function renderImprovement(payload){
  $("improvementDate").textContent=`Cập nhật ${payload.updated_at}`;
  $("improvementMessage").textContent=payload.message;
  $("improvementDone").textContent=payload.counts.complete_engineering||0;
  $("improvementProgress").textContent=payload.counts.in_progress||0;
  $("improvementWaiting").textContent=payload.counts.waiting_for_domain_data||0;
  const target=$("improvementRoadmap");target.replaceChildren();
  payload.milestones.forEach(item=>{
    const card=document.createElement("article");card.className=`improvement-item ${item.status}`;
    const head=document.createElement("div");head.className="improvement-head";
    const step=document.createElement("span");step.textContent=String(item.order).padStart(2,"0");
    const title=document.createElement("h3");title.textContent=item.title;
    const status=document.createElement("b");status.textContent=improvementStatusNames[item.status]||item.status;
    head.append(step,title,status);
    const rows=document.createElement("div");rows.className="improvement-details";
    [
      ["Bằng chứng hiện tại",item.technical_evidence],
      ["Metric hiện có",item.current_metric],
      ["Giúp nghiệp vụ gì?",item.business_value],
      ["KPI nghiệp vụ",item.business_kpi],
      ["Điều kiện được xem là đạt",item.gate],
      ["Việc tiếp theo",item.next_action],
      ["Đang thiếu",item.blocked_by],
    ].forEach(([label,value])=>{const row=document.createElement("div");const name=document.createElement("b");name.textContent=label;const text=document.createElement("p");text.textContent=value;row.append(name,text);rows.append(row)});
    card.append(head,rows);target.append(card);
  });
}
async function load(){
  setError("");$("reload").disabled=true;
  try{const [health,rows,proof,improvement,jobs]=await Promise.all([api.health(),api.listClaims(),api.modelEvidence(),api.improvementStatus(),api.listAnalysisJobs()]);const active=new Map(jobs.filter(job=>["queued","running"].includes(job.status)).map(job=>[job.claim_id,job]));claims=rows.map(row=>{const job=active.get(row.claim_id);return job?{...row,analysis_status:"analyzing",priority:"analyzing",priority_reason:`${job.message} · ${Math.floor(job.elapsed_seconds||0)} giây`,job_message:job.message}:row});const warmup=proof.runtime?.modules?.document_pipeline?.warmup?.status;const warmupLabel=warmup==="ready"?"model sẵn sàng":["scheduled","warming"].includes(warmup)?"đang nạp model":warmup==="error"?"model chứng từ lỗi":"model tải khi cần";$("modeBadge").textContent=`${health.mode.toUpperCase()} · ${warmupLabel}`;$("sideMode").textContent=`${health.product_version} · ${warmupLabel}`;stat();renderQueue();renderImprovement(improvement);renderProof(proof)}catch(error){setError(`Không tải được dashboard: ${error.message}`)}finally{$("reload").disabled=false}
}
[$("search"),$("statusFilter"),$("priorityFilter"),$("decisionFilter")].forEach(element=>element.addEventListener("input",renderQueue));
$("reload").addEventListener("click",load);
load();
