import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, FileText, Radar, Search } from "lucide-react";

export const metadata: Metadata = {
  title: "대한전선 미국 전력망·데이터센터 수주 인텔리전스 | ElecBidSpec AI",
  description:
    "대한전선의 전력 케이블, EHV, HVDC, 가공선, 배전, 해저케이블 역량에 맞춰 미국 전력망·데이터센터 초기 신호와 입찰 준비를 연결하는 AI 워크스페이스.",
};

const sourceStats = [
  { value: "44", label: "미국 공식 소스 추적" },
  { value: "$5M+", label: "우선 검토 인프라 프로젝트" },
  { value: "IOU", label: "민간 투자자 소유 전력회사 신호 분리" },
  { value: "Pre-RFP", label: "AVL·사전 적격 등록 타이밍 포착" },
];

const taihanFacts = [
  {
    value: "1941",
    label: "대한민국 최초 전선기업",
    href: "https://www.taihan.com/en/company/overview",
  },
  {
    value: "100+",
    label: "100개국 이상 진출한 글로벌 네트워크",
    href: "https://www.taihan.com/en/company/overview",
  },
  {
    value: "EHV/HVDC",
    label: "송전 케이블 및 접속재 포트폴리오",
    href: "https://www.taihan.com/en/business/product/electricity",
  },
  {
    value: "CLV",
    label: "해저케이블 및 해상풍력 밸류체인",
    href: "https://www.taihan.com/en/business/solutionDetail?idx=10",
  },
];

const outcomes = [
  "연방·주정부·전력회사·교통국·공항·데이터센터·재생에너지·공공기관 공고와 초기 신호를 하나의 기준으로 연결합니다.",
  "EHV, HVDC, 가공선, MV/LV 배전, 해저·해상풍력, 접속재, 변전소, 시공 파트너 필요 여부를 구매 잡음에서 분리합니다.",
  "유망 신호와 공고를 대한전선 관점의 사전 적격 등록, 입찰/비입찰 판단 메모, 컴플라이언스 매트릭스, 누락정보 체크리스트, 파트너 이메일, 경영진 요약으로 전환합니다.",
];

const workflow = [
  {
    icon: Radar,
    title: "미국 전력망 초기 신호 상시 감시",
    copy: "SAM.gov와 공공 포털뿐 아니라 PUC docket, RTO/ISO 송전계획, 대규모 부하 접속, 변전소 인허가, 전력회사 자본계획 신호를 분리해 봅니다.",
  },
  {
    icon: Search,
    title: "대한전선 역량과 AVL 타이밍 기준 우선순위화",
    copy: "지역, 예상 규모, 케이블 유형, 지중·가공·변전소 범위, IOU 여부, 설치 파트너 필요 여부, 사전 적격 등록 가능성을 대한전선 기준으로 정렬합니다.",
  },
  {
    icon: FileText,
    title: "제안 준비 패키지 생성",
    copy: "각 공고를 범위 체크리스트, 리스크 요약, 컴플라이언스 매트릭스, 경영진 요약, 파트너 접촉 이메일로 전환합니다.",
  },
];

const proof = [
  {
    title: "EHV/HVDC 케이블 범위 감지",
    copy: "초고압 송전 계통 공고를 일반 전기공사와 분리해 우선 검토 대상으로 올립니다.",
  },
  {
    title: "PUC·RTO·인허가 초기 신호 분리",
    copy: "비공개 전력회사 RFP가 열리기 전에 공개 규제·계획·인허가 문서에서 수주 움직임을 읽습니다.",
  },
  {
    title: "가공선·배전·변전소 키워드 추출",
    copy: "발주서 문장 안의 자재, 접속재, 관로, 변압기, 변전소 범위를 빠르게 구조화합니다.",
  },
  {
    title: "해저케이블·해상풍력 신호 식별",
    copy: "항만, 해상풍력, 해저 전력망 발주 언어를 별도 기회 신호로 표시합니다.",
  },
  {
    title: "시공 파트너·EPC 접촉 초안",
    copy: "공급 단독인지, 설치·EPC 협력이 필요한지 판단하고 바로 보낼 이메일을 준비합니다.",
  },
  {
    title: "소스 헬스와 포털 접근 상태",
    copy: "정상 소스, 포털 제한, 매칭 없음, 설정 필요 상태를 나눠 커버리지 신뢰도를 보입니다.",
  },
  {
    title: "대한전선 맞춤 제안 문구",
    copy: "회사 프로필의 강점을 경영진 요약과 제안 체크리스트에 자연스럽게 반영합니다.",
  },
];

export default function TaihanPage() {
  return (
    <main className="sales-page" lang="ko">
      <section className="sales-hero">
        <div className="sales-nav">
          <Link href="/taihan" className="sales-brand" aria-label="ElecBidSpec AI 대한전선 소개 페이지">
            <span>ElecBidSpec AI | 대한전선</span>
          </Link>
          <nav aria-label="소개 페이지 내비게이션">
            <a href="#coverage">커버리지</a>
            <a href="#workflow">워크플로</a>
            <a href="#pilot">파일럿</a>
            <Link href="/">앱 열기</Link>
          </nav>
        </div>

        <img
          className="sales-hero-visual"
          src="/assets/elecbidspec-console-preview-dark.svg"
          alt="소스 상태, 우선 검토 공고, 적합도 점수, 제안 산출물을 보여주는 ElecBidSpec AI 플랫폼 미리보기"
        />
        <div className="sales-hero-overlay" aria-hidden="true"></div>

        <div className="sales-hero-content">
          <p className="sales-kicker">미래를 연결하는 기술, 미국 공공입찰까지</p>
          <h1>대한전선의 미국 전력망·데이터센터 수주 신호를 먼저 포착합니다.</h1>
          <p className="sales-hero-copy">
            미국 전력망 시장의 핵심 프로젝트는 공개 입찰보다 먼저 PUC, RTO/ISO, 인허가, 대규모 부하 접속, 전력회사 자본계획에서 움직입니다. ElecBidSpec AI는 그 초기 신호를 대한전선의 EHV/HVDC·XLPE·가공선·배전·해저케이블 역량과 연결해 수주 검토와 제안 준비까지 한 흐름으로 정리합니다.
          </p>
          <div className="sales-actions">
            <Link href="/" className="sales-primary">
              라이브 도구 열기
              <ArrowRight size={18} />
            </Link>
            <a href="#pilot" className="sales-secondary">
              파일럿 구성 보기
            </a>
          </div>
          <dl className="sales-hero-stats" aria-label="플랫폼 핵심 지표">
            <div>
              <dt>미국</dt>
              <dd>전력망 신호 레이더</dd>
            </div>
            <div>
              <dt>$5M+</dt>
              <dd>우선 검토 대상</dd>
            </div>
            <div>
              <dt>대한전선</dt>
              <dd>역량 맥락 내장</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="sales-lineage sales-section-pad">
        <div className="sales-section-inner sales-two-column">
          <p className="sales-kicker">대한전선 맞춤 포지셔닝</p>
          <h2>미국 IOU 프로젝트는 입찰 공고가 아니라 관계와 적격 등록에서 먼저 갈립니다.</h2>
          <p>
            대한전선의 경쟁력은 단순 케이블 공급에 머물지 않습니다. 전력 인프라, 토털 케이블 솔루션, EHV/HVDC 시스템, 가공선·배전 제품, 해저케이블 실행 역량까지 이어집니다. 이 파일럿은 그 역량을 미국 전력회사·데이터센터 프로젝트를 읽는 기준으로 바꾸고, 비공개 조달 포털에 들어가기 전 사전 적격 등록과 파트너 접촉 타이밍을 앞당깁니다.
          </p>
        </div>
      </section>

      <section className="sales-section-pad sales-source-band">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">역량 기준</p>
            <h2>대한전선이 이미 증명한 기술 영역을 기준으로 기회를 선별합니다.</h2>
            <p>
              제안 보조 기능은 대한전선의 공개 역량 프로필을 바탕으로 전력 송배전, EHV/HVDC, 가공선, MV/LV 배전, 케이블 접속재, 해상풍력, 해저케이블, 글로벌 납품 경험을 문맥으로 사용합니다.
            </p>
          </div>
          <div className="sales-fact-grid">
            {taihanFacts.map((fact) => (
              <a className="sales-fact-card" href={fact.href} key={fact.label} target="_blank" rel="noreferrer">
                <strong>{fact.value}</strong>
                <span>{fact.label}</span>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band" id="coverage">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">미국 시장 실시간 리드</p>
            <h2>전국 공식 소스를 대한전선 관점의 전력망·데이터센터 기회로 정렬합니다.</h2>
            <p>
              커버리지의 빈틈도 투명하게 보여줍니다. 활성 공고, 초기 신호, 포털 제한, 매칭 없음, 설정 필요 상태를 분리해 어느 전력회사와 지역 시장을 더 깊게 연결해야 하는지 판단할 수 있습니다.
            </p>
          </div>
          <div className="sales-stat-grid">
            {sourceStats.map((item) => (
              <div className="sales-stat" key={item.label}>
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-section-pad" id="workflow">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">공고 발견에서 수주 검토까지</p>
            <h2>초기 신호, AVL 등록, 파트너 시공, 제안 준비를 한 흐름으로 묶습니다.</h2>
            <p>
              PUC/RTO/인허가 신호 확인, 기술 범위 추출, 적합도 점수, 저장 검색, 파트너 접촉, 제안 산출물을 하나의 워크스페이스에서 처리합니다.
            </p>
          </div>
          <div className="sales-workflow-grid">
            {workflow.map((item) => {
              const Icon = item.icon;
              return (
                <article className="sales-workflow-card" key={item.title}>
                  <Icon size={22} />
                  <h3>{item.title}</h3>
                  <p>{item.copy}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band">
        <div className="sales-section-inner sales-code-layout">
          <div className="sales-code-copy">
            <p className="sales-kicker">대한전선이 바로 체감할 가치</p>
            <h2>공고가 뜬 뒤 쫓아가는 시간을 줄이고, 먼저 움직일 미국 파이프라인만 남깁니다.</h2>
            <p>
              대한전선의 영업·사업개발팀은 첫 사용부터 우선순위가 매겨진 미국 전력망·데이터센터 기회, 각 신호가 중요한 이유, 소스 상태, 저장 검색, 파트너·EPC·유통사·내부 검토자에게 넘길 수 있는 제안 자료를 확인할 수 있습니다.
            </p>
            <ul className="sales-feature-list">
              {outcomes.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="sales-code-panel" aria-label="입찰 인텔리전스 예시 기록">
            <div className="sales-tabs">
              <span>공고</span>
              <span>적합도</span>
              <span>제안</span>
            </div>
            <pre className="sales-code-block"><code>{`{
  "소스": "JEA",
  "단계": "early_signal",
  "소유자": "investor_owned_utility",
  "프로젝트": "AI 데이터센터 230kV 접속 신호",
  "회사맥락": "대한전선",
  "적합도점수": 88,
  "역량신호": ["EHV", "XLPE", "변전소", "데이터센터"],
  "주목이유": [
    "PUC/RTO 단계에서 먼저 포착",
    "$5M+ 검토 대상 가능성",
    "AVL 등록과 시공 파트너 접촉 타이밍",
    "시공 파트너 접촉 초안 생성"
  ]
}`}</code></pre>
          </div>
        </div>
      </section>

      <section className="sales-section-pad" id="platform">
        <div className="sales-section-inner">
          <div className="sales-section-heading compact">
            <p className="sales-kicker">파일럿 플랫폼</p>
            <h2>대한전선 미국 시장 파일럿에 필요한 것부터 검증 가능하게.</h2>
          </div>
          <div className="sales-platform-grid">
            {proof.map((item) => (
              <article className="sales-platform-item" key={item.title}>
                <h3>{item.title}</h3>
                <p>{item.copy}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band" id="pilot">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">파일럿 구성</p>
            <h2>미국 입찰 레이더에서 실제 수주 운영으로 이어지는 현실적인 경로.</h2>
            <p>
              낮은 운영비의 미국 공공입찰 파일럿으로 시작하고, 사용 가치가 확인되는 순서대로 심화 소스 어댑터, 전용 사용자 계정, 관리형 제안 워크플로를 확장합니다.
            </p>
          </div>
          <div className="sales-plan-grid">
            <article className="sales-plan">
              <h3>시장 탐색 파일럿</h3>
              <p>한 팀이 미국 공공 기회 커버리지와 입찰/비입찰 판단 흐름을 검증하는 단계입니다.</p>
              <ul>
                <li>라이브 대시보드와 소스 헬스</li>
                <li>수동 업로드와 사양 추출</li>
                <li>저장 검색과 다이제스트 실행</li>
              </ul>
            </article>
            <article className="sales-plan featured">
              <h3>수주 추진 파일럿</h3>
              <p>영업, 사업개발, 파트너팀이 제안 준비 가치를 검증하는 단계입니다.</p>
              <ul>
                <li>대한전선 맞춤 회사 맥락</li>
                <li>DOCX/PDF 제안 초안</li>
                <li>일일 저장 검색 알림</li>
              </ul>
            </article>
            <article className="sales-plan">
              <h3>커버리지 확장</h3>
              <p>대한전선에 중요한 미국 포털, 전력회사, 교통국, 지방 공공기관을 추가하는 단계입니다.</p>
              <ul>
                <li>주요 DOT와 전력회사 확대</li>
                <li>소스별 첨부파일 수집 개선</li>
                <li>관리자 권한과 테넌트 분리</li>
              </ul>
            </article>
          </div>
        </div>
      </section>

      <section className="sales-cta-band">
        <div className="sales-section-inner sales-cta-content">
          <div>
            <p className="sales-kicker">대한전선 검토용</p>
            <h2>일반 SaaS 데모가 아니라, 대한전선 기준으로 검증 가능한 미국 수주 워크스페이스.</h2>
          </div>
          <div className="sales-cta-actions">
            <Link href="/" className="sales-primary">
              앱 실행
              <ArrowRight size={18} />
            </Link>
            <a href="#coverage" className="sales-secondary on-dark">
              커버리지 보기
            </a>
          </div>
        </div>
      </section>

      <footer className="sales-footer">
        <span>©2026 SUPREME AI VENTURES LLC</span>
        <span>대한전선의 미국 공공입찰 인텔리전스와 제안 준비를 위한 파일럿.</span>
      </footer>
    </main>
  );
}
