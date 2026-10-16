const byId=id=>document.getElementById(id), message=byId("message");
let activeClaim=null,captureSession=null,demoEnabled=false,regularEvidenceUploaded=false;
const sampleFeatures={months_as_customer:166,age:37,policy_number:900001,policy_bind_date:"2008-06-19",policy_state:"IL",policy_csl:"100/300",policy_deductable:2000,policy_annual_premium:1337.28,umbrella_limit:8000000,insured_zip:700001,insured_sex:"MALE",insured_education_level:"JD",insured_occupation:"craft-repair",insured_hobbies:"reading",insured_relationship:"husband",capital_gains:27500,capital_loss:0,incident_date:"2015-02-28",incident_type:"Multi-vehicle Collision",collision_type:"Side Collision",incident_severity:"Major Damage",authorities_contacted:"Police",incident_state:"WV",incident_city:"Riverwood",incident_location:"Synthetic location 1",incident_hour_of_the_day:10,number_of_vehicles_involved:3,property_damage:"NO",bodily_injuries:2,witnesses:2,police_report_available:null,total_claim_amount:67140,injury_claim:7460,property_claim:7460,vehicle_claim:52220,auto_make:"Ford",auto_model:"F150",auto_year:2006};
const stageNames={queued:"Đang chờ lượt",preparing:"Kiểm tra dữ liệu/cache",tabular:"Chấm điểm dữ liệu bảng",evidence:"Chuẩn bị bằng chứng",image_authenticity:"Kiểm tra nguồn gốc ảnh",damage:"YOLO khoanh vùng hư hỏng",vehicle_plate:"Đọc biển số trên ảnh",document_loading:"Chuẩn bị model chứng từ",document_classifier:"DiT nhận dạng chứng từ",document_ocr:"PaddleOCR đọc chữ",document_kie:"LayoutLMv3 trích xuất trường",relationships:"Đối chiếu quan hệ",finalizing:"Tổng hợp kết quả",completed:"Kết quả đã sẵn sàng"};
const stageDetails={queued:"Job đang chờ tài nguyên suy luận.",preparing:"Hệ thống kiểm tra kết quả có thể dùng lại trước khi chạy model.",tabular:"XGBoost đang tính điểm xếp hạng hàng đợi.",evidence:"Đang chuẩn bị ảnh và chứng từ cho các module tương ứng.",image_authenticity:"Đang kiểm tra metadata, provenance và ảnh đã xuất hiện ở hồ sơ khác.",damage:"YOLOv8s-seg đang tìm và khoanh vùng hư hỏng trên ảnh xe.",vehicle_plate:"OCR cục bộ đang tìm chuỗi biển số nhìn thấy được; kết quả không lấy từ ô khai báo.",document_loading:"Lần đầu có thể chậm vì cần nạp DiT, PaddleOCR và LayoutLMv3 vào bộ nhớ.",document_classifier:"DiT đang xác định loại chứng từ.",document_ocr:"PaddleOCR đang nhận dạng từng vùng chữ; đây thường là bước lâu nhất trên CPU.",document_kie:"LayoutLMv3 đang trích ngày, tổng tiền và các trường cần đối chiếu.",relationships:"NetworkX đang so khớp đầu mối với các hồ sơ có trước.",finalizing:"Đang ghép kết quả kỹ thuật thành hướng xử lý nghiệp vụ."};

function makeClaimId(){const now=new Date(),p=n=>String(n).padStart(2,"0");return `CLM-${now.getFullYear()}${p(now.getMonth()+1)}${p(now.getDate())}-${p(now.getHours())}${p(now.getMinutes())}${p(now.getSeconds())}-${Math.floor(Math.random()*900+100)}`}
function setStep(id,state,text){const node=byId(id);node.className=`progress-step ${state}`;node.querySelector("span").textContent=text}
function newClaim(){activeClaim=null;captureSession=null;regularEvidenceUploaded=false;byId("claimId").value=makeClaimId();["stepStore","stepUpload","stepAnalyze","stepOpen"].forEach(id=>setStep(id,"","Chờ thực hiện"))}
function setMessage(text,error=false){message.textContent=text;message.classList.toggle("error",error)}
async function showServerState(){
  try{
    const response=await fetch("/readiness"),payload=await response.json();
    if(!response.ok)throw new Error(payload.detail||JSON.stringify(payload));
    const documentModule=payload.modules?.document_pipeline||{},warmup=documentModule.warmup||{};
    if(!documentModule.active)setMessage("Model đọc chứng từ chưa được cài trên máy chủ. Ảnh và các module còn lại vẫn có thể chạy; phần thiếu sẽ được ghi rõ trong kết quả.");
    else if(["scheduled","warming"].includes(warmup.status))setMessage("Máy chủ đang nạp DiT, PaddleOCR và LayoutLMv3 vào bộ nhớ. Bạn vẫn có thể tạo hồ sơ; bước chứng từ sẽ chờ model sẵn sàng thay vì nạp lại từ đầu.");
    else if(warmup.status==="error")setMessage(`Không nạp sẵn được model chứng từ: ${warmup.error||"lỗi chưa xác định"}. Hệ thống sẽ ghi rõ module không chạy được.`,true);
    else if(warmup.status==="ready")setMessage("Các model chứng từ đã được nạp sẵn. Hồ sơ mới sẽ bỏ qua thời gian khởi động model.");
  }catch(error){setMessage(`Chưa đọc được trạng thái model: ${error.message}`,true)}
}
function listFiles(input,target){byId(target).textContent=[...input.files].map(file=>`${file.name} · ${(file.size/1024).toFixed(1)} KB`).join("\n")||"Chưa chọn tệp."}
function formatElapsed(seconds){const total=Math.max(0,Math.floor(seconds||0));return `${String(Math.floor(total/60)).padStart(2,"0")}:${String(total%60).padStart(2,"0")}`}
function slowestStage(job){const rows=Object.entries(job.stage_durations_seconds||{}).filter(([,seconds])=>Number(seconds)>0).sort((a,b)=>Number(b[1])-Number(a[1]));if(!rows.length)return null;const [stage,seconds]=rows[0];return {stage:stageNames[stage]||stage,seconds:Number(seconds)}}
function updateJobPanel(claimId,job){const panel=byId("jobHelp"),link=byId("openResult"),elapsed=Number(job.elapsed_seconds||0),stageElapsed=Number(job.current_stage_elapsed_seconds||0);panel.hidden=false;byId("jobStageTitle").textContent=`${stageNames[job.stage]||job.message} · ${formatElapsed(elapsed)}`;let detail=stageDetails[job.stage]||job.message;if(["queued","running"].includes(job.status))detail+=` Công đoạn hiện tại đã chạy ${formatElapsed(stageElapsed)}.`;const slowest=slowestStage(job);if(job.status==="completed"&&slowest)detail+=` Công đoạn lâu nhất: ${slowest.stage} (${formatElapsed(slowest.seconds)}).`;if(elapsed>=180&&["queued","running"].includes(job.status))detail+=" Job đã chạy hơn 3 phút; vẫn có thể mở Hàng đợi để theo dõi mà không làm dừng tiến trình.";byId("jobStageDetail").textContent=detail;link.href=`/?view=workbench&claim_id=${encodeURIComponent(claimId)}`;link.hidden=!job.result_available;byId("result").textContent=JSON.stringify(job,null,2)}

byId("images").onchange=()=>listFiles(byId("images"),"imageList");
byId("documents").onchange=()=>listFiles(byId("documents"),"documentList");
byId("demoMode").onclick=()=>{demoEnabled=!demoEnabled;byId("demoMode").classList.toggle("active",demoEnabled);byId("demoMode").textContent=demoEnabled?"Hồ sơ mẫu đang bật":"Dùng hồ sơ mẫu";if(demoEnabled){byId("amount").value=67140;byId("incidentDate").value="2015-02-28";byId("plate").value="51G-001.88";byId("contactPhone").value="0909000111";byId("repairShop").value="GARAGE-DEMO-01";setMessage("Đã bật feature nghiệp vụ mô phỏng để XGBoost có thể chấm điểm. Dùng lại điện thoại/xưởng ở hồ sơ sau để demo quan hệ.")}else setMessage("Đã tắt feature mô phỏng. Ảnh và chứng từ vẫn được phân tích; XGBoost có thể ghi Chưa chấm nếu thiếu dữ liệu bảng.")};

function intakePayload(){const relationshipEntities={};if(byId("contactPhone").value.trim())relationshipEntities.contact_phone=byId("contactPhone").value.trim();if(byId("repairShop").value.trim())relationshipEntities.repair_shop=byId("repairShop").value.trim();return {claim_amount:byId("amount").value?Number(byId("amount").value):null,incident_date:byId("incidentDate").value||null,plate_number:byId("plate").value||null,relationship_entities:relationshipEntities,tabular_features:demoEnabled?sampleFeatures:{}}}

async function ensureClaimCreated(){
  if(activeClaim)return activeClaim;
  const claimId=byId("claimId").value;
  setStep("stepStore","active","Đang tạo hồ sơ…");
  const response=await fetch(`/claims/${claimId}/intake`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(intakePayload())});
  if(!response.ok){const payload=await response.json().catch(()=>({detail:"Không tạo được hồ sơ."}));if(response.status===409){newClaim();throw new Error("Mã hồ sơ vừa bị trùng. Hệ thống đã tạo mã mới; hãy thực hiện lại.")}throw new Error(payload.detail||JSON.stringify(payload))}
  activeClaim=claimId;setStep("stepStore","done","Đã lưu");return claimId;
}

async function uploadFiles(claimId,kind,files){for(const file of files){const body=new FormData();body.append("kind",kind);body.append("file",file);const response=await fetch(`/claims/${claimId}/evidence`,{method:"POST",body});if(!response.ok)throw new Error(`${file.name}: ${await response.text()}`)}}

async function pollJob(claimId,job){
  let current=job,pollFailures=0;
  while(["queued","running"].includes(current.status)){
    updateJobPanel(claimId,current);
    setStep("stepAnalyze","active",`${stageNames[current.stage]||current.message} · ${formatElapsed(current.elapsed_seconds)}`);
    setMessage(`${current.message} Lần đầu chạy đầy đủ trên CPU thường mất 1–3 phút; mở Hàng đợi không làm dừng job.`);
    await new Promise(resolve=>setTimeout(resolve,1000));
    try{
      const response=await fetch(`/claims/${claimId}/analysis-jobs/${current.job_id}`);
      current=await response.json();
      if(!response.ok)throw new Error(current.detail||JSON.stringify(current));
      pollFailures=0;
    }catch(error){pollFailures+=1;if(pollFailures>=5)throw new Error(`Mất kết nối khi theo dõi job: ${error.message}. Job có thể vẫn chạy; hãy mở Hàng đợi để kiểm tra.`);setMessage(`Kết nối theo dõi bị gián đoạn (${pollFailures}/5). Đang thử lại; job trên máy chủ vẫn tiếp tục.`)}
  }
  if(current.status==="failed")throw new Error(current.error||"Phân tích gặp lỗi.");
  updateJobPanel(claimId,current);
  return current;
}

byId("analyze").onclick=async()=>{const button=byId("analyze");try{
  const images=byId("images").files,documents=byId("documents").files;
  if(!activeClaim&&!images.length&&!documents.length)throw new Error("Hãy chọn ít nhất một ảnh xe hoặc chứng từ.");
  button.disabled=true;button.textContent="Đang phân tích…";message.classList.remove("error");setMessage("Đang lưu hồ sơ…");
  const claimId=await ensureClaimCreated();
  if(!regularEvidenceUploaded){setStep("stepUpload","active","Đang hash và kiểm tra…");setMessage("Đang tải và kiểm tra bằng chứng…");await uploadFiles(claimId,"image",images);await uploadFiles(claimId,"document",documents);regularEvidenceUploaded=true;setStep("stepUpload","done",`Đã lưu ${images.length+documents.length} tệp`)}
  setStep("stepAnalyze","active","Đang khởi tạo job nền…");
  const start=await fetch(`/claims/${claimId}/analysis-jobs`,{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});
  const job=await start.json();if(!start.ok)throw new Error(job.detail||JSON.stringify(job));
  const finished=await pollJob(claimId,job);
  const analysisResponse=await fetch(`/claims/${claimId}/analysis`);const payload=await analysisResponse.json();if(!analysisResponse.ok)throw new Error(payload.detail||JSON.stringify(payload));
  byId("result").textContent=JSON.stringify({job:finished,analysis:payload},null,2);
  setStep("stepAnalyze","done",`${payload.analysis_status==="complete"?"Hoàn tất":"Hoàn tất một phần"} · ${formatElapsed(finished.elapsed_seconds)}${finished.cache_hit?" · dùng cache":""}`);
  const slowest=slowestStage(finished),bottleneck=slowest?` Công đoạn lâu nhất: ${slowest.stage} (${formatElapsed(slowest.seconds)}).`:"";
  setStep("stepOpen","done","Kết quả sẵn sàng");setMessage(`Phân tích hoàn tất sau ${formatElapsed(finished.elapsed_seconds)}.${bottleneck} Bạn có thể bấm Mở kết quả hoặc chờ hệ thống tự chuyển trang.`);
  setTimeout(()=>location.href=`/?view=workbench&claim_id=${encodeURIComponent(claimId)}`,1800);
}catch(error){button.disabled=false;button.textContent="Phân tích hồ sơ";setMessage(error.message,true);const active=[...document.querySelectorAll(".progress-step.active")].pop();if(active){active.classList.remove("active");active.classList.add("error");active.querySelector("span").textContent="Cần xử lý"}}};

byId("capture").onclick=async()=>{try{
  setMessage("Đang lưu hồ sơ và tạo yêu cầu chụp có thời hạn…");const claimId=await ensureClaimCreated();
  const response=await fetch(`/claims/${claimId}/capture-sessions`,{method:"POST"});captureSession=await response.json();if(!response.ok)throw new Error(captureSession.detail||JSON.stringify(captureSession));
  byId("capturePanel").hidden=false;byId("captureSteps").replaceChildren(...captureSession.instructions.map(item=>{const label=document.createElement("label");label.className="upload";label.textContent=`Bước ${item.step}: ${item.instruction}`;const input=document.createElement("input");input.type="file";input.accept="image/*";input.capture="environment";input.dataset.step=item.step;label.appendChild(input);return label}));
  setMessage(`Phiên ${captureSession.session_id.slice(0,8)} hết hạn lúc ${new Date(captureSession.expires_at).toLocaleTimeString("vi-VN")}. Ảnh sẽ được gắn đúng bước và hash để truy vết.`);
}catch(error){setMessage(`Không tạo được phiên chụp: ${error.message}`,true)}};

byId("uploadCapture").onclick=async()=>{try{const inputs=[...byId("captureSteps").querySelectorAll('input[type="file"]')];if(inputs.some(input=>!input.files[0]))throw new Error("Cần chọn đủ ba ảnh theo ba hướng dẫn.");for(const input of inputs){const body=new FormData();body.append("kind","image");body.append("capture_session_id",captureSession.session_id);body.append("challenge_step",input.dataset.step);body.append("file",input.files[0]);const response=await fetch(`/claims/${activeClaim}/evidence`,{method:"POST",body});if(!response.ok)throw new Error(await response.text())}setMessage("Đã lưu đủ 3 ảnh có kiểm soát. Bây giờ bấm Phân tích hồ sơ.")}catch(error){setMessage(`Không tải được phiên chụp: ${error.message}`,true)}};

newClaim();showServerState();
