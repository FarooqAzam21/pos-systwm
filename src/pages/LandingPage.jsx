import { useState } from 'react'
import {
  ArrowDown, ArrowRight, ArrowUpRight, BarChart3, Boxes, CalendarCheck,
  Check, ChevronDown, CreditCard, Menu, PackageCheck, ReceiptText, Settings2,
  ShieldCheck, ShoppingCart, Store, Users, Wallet, X,
} from 'lucide-react'
import BrandLogo from '../components/BrandLogo'
import './LandingPage.css'

const APP_LOGIN = 'https://pos-systwm.vercel.app/login'

const features = [
  { icon: ShoppingCart, title: 'Checkout that stays organized', text: 'Record sales with product line items, discounts, tax, payments, and customer details in one consistent workflow.' },
  { icon: Boxes, title: 'Know what is on your shelves', text: 'Keep product, category, stock movement, and supplier records together, with low-stock and out-of-stock visibility.' },
  { icon: Users, title: 'Keep customer balances clear', text: 'Save customer contact details, view purchase history, record payments, and see outstanding balances.' },
  { icon: Wallet, title: 'Make operating costs visible', text: 'Record expenses by category, date, and payment method to include day-to-day costs in your business overview.' },
  { icon: BarChart3, title: 'Turn activity into useful reports', text: 'Review sales, purchases, inventory, expenses, payments, customers, profitability, and profit-and-loss reports. Export supported reports to PDF or Excel.' },
  { icon: CalendarCheck, title: 'Close each day with a record', text: 'Compare expected and actual closing cash and keep a dated record of daily sales, payments, expenses, and variance.' },
  { icon: Settings2, title: 'Set up your business workspace', text: 'Manage business details, currency, timezone, invoices, account settings, and staff access with role-based permissions.' },
  { icon: ShieldCheck, title: 'Review important activity', text: 'Authorized owners and admins can review recorded changes and actions in the audit log.' },
]

const workflow = [
  { number: '01', title: 'Organize products', text: 'Add products, categories, suppliers, and starting stock.' },
  { number: '02', title: 'Record sales', text: 'Check out products, attach customer details, and record payment.' },
  { number: '03', title: 'Track activity', text: 'Keep purchases, expenses, payments, and stock movement in view.' },
  { number: '04', title: 'Review and close', text: 'Use reports to review performance and complete the daily closing.' },
]

const benefits = [
  'Keep sales and business records organized in one workspace.',
  'Spend less time repeating manual record keeping for recorded activity.',
  'See operating expenses alongside sales and inventory reporting.',
  'Keep stock levels, supplier purchases, and transactions easier to review.',
  'Bring routine checkout and end-of-day tasks into a consistent flow.',
  'Give each team member access that matches their assigned role.',
]

const faqs = [
  { question: 'What is The Orvion POS?', answer: 'It is a business workspace for recording point-of-sale transactions and managing related inventory, customers, supplier purchases, expenses, payments, and reports.' },
  { question: 'What can I manage with it?', answer: 'The application includes sales checkout, products and stock, customers, suppliers and purchases, expenses, payments, reports, daily closing, business settings, and user roles.' },
  { question: 'How do I access the application?', answer: 'Use any Access POS or Open Your POS button on this page to open the existing sign-in screen.' },
  { question: 'Can I track sales, expenses, and inventory?', answer: 'Yes. Sales, expenses, inventory levels and movements, and related financial summaries are available in the application.' },
  { question: 'How do I get started?', answer: 'Create a business workspace from the registration screen. The first account becomes the workspace owner and can set up products, business details, and team access.' },
  { question: 'Does the system require an account?', answer: 'Yes. You need an account to access a business workspace. Registration creates a business and its first owner account together.' },
]

function Brand({ footer = false }) {
  return <a className={`orvion-brand${footer ? ' footer-brand' : ''}`} href="#top" aria-label="The Orvion POS home">
    <BrandLogo className="orvion-logo" />
  </a>
}

function DashboardPreview({ large = false }) {
  return <div className={`preview-frame${large ? ' preview-frame-large' : ''}`} aria-label="Illustrative preview of the POS dashboard">
    <div className="preview-sidebar">
      <div className="preview-side-brand"><BrandLogo className="preview-mini-logo" /><b>orvion</b></div>
      <span className="preview-nav-label">WORKSPACE</span>
      <span className="preview-nav active"><span>⌂</span> Dashboard</span>
      <span className="preview-nav"><span>▣</span> Point of sale</span>
      <span className="preview-nav"><span>↗</span> Sales</span>
      <span className="preview-nav"><span>⬡</span> Inventory</span>
      <span className="preview-nav"><span>◎</span> Customers</span>
      <div className="preview-side-bottom"><i /> Workspace ready</div>
    </div>
    <div className="preview-main">
      <div className="preview-topbar"><span>Business overview</span><span className="preview-user"><i>S</i> Store team <ChevronDown size={12} /></span></div>
      <div className="preview-content">
        <div className="preview-title"><div><small>BUSINESS OVERVIEW</small><h3>Good morning</h3><p>Here’s a snapshot of your business.</p></div><span className="preview-period">Last 7 days <ChevronDown size={12} /></span></div>
        <div className="preview-metrics">
          <div className="preview-metric"><small>Net revenue</small><strong>PKR 48,250</strong><span><b>↗</b> Sales recorded</span></div>
          <div className="preview-metric"><small>Transactions</small><strong>126</strong><span>Across selected period</span></div>
          <div className="preview-metric"><small>Operating expenses</small><strong>PKR 8,420</strong><span>Recorded this period</span></div>
        </div>
        <div className="preview-chart-card"><div className="preview-chart-heading"><div><b>Sales trend</b><small>Net sales recorded per day</small></div><span>Last 7 days</span></div>
          <div className="preview-chart">
            <div className="preview-y-labels"><span>15k</span><span>10k</span><span>5k</span><span>0</span></div>
            <svg viewBox="0 0 520 142" preserveAspectRatio="none" role="img" aria-label="Illustrative upward and downward weekly sales trend">
              <defs><linearGradient id="previewFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#7392ff" stopOpacity=".25"/><stop offset="1" stopColor="#7392ff" stopOpacity="0"/></linearGradient></defs>
              <path d="M0 112 C28 104 37 87 68 91 S113 109 145 78 S190 90 216 62 S257 77 286 53 S321 71 356 45 S399 53 427 34 S473 54 520 18 V142 H0Z" fill="url(#previewFill)"/>
              <path d="M0 112 C28 104 37 87 68 91 S113 109 145 78 S190 90 216 62 S257 77 286 53 S321 71 356 45 S399 53 427 34 S473 54 520 18" fill="none" stroke="#738dff" strokeWidth="3" vectorEffect="non-scaling-stroke"/>
            </svg>
            <div className="preview-x-labels"><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span></div>
          </div>
        </div>
        <div className="preview-lower"><div className="preview-stock"><b>Stock status</b><div><i className="stock-dot in-stock"/> In stock <strong>72</strong></div><div><i className="stock-dot low-stock"/> Low stock <strong>9</strong></div><div><i className="stock-dot out-stock"/> Out of stock <strong>3</strong></div></div><div className="preview-stock"><b>Recent activity</b><div><span className="activity-icon">↗</span> Sale recorded <small>Just now</small></div><div><span className="activity-icon violet">＋</span> Stock received <small>Today</small></div><div><span className="activity-icon amber">−</span> Expense recorded <small>Today</small></div></div></div>
      </div>
    </div>
    <span className="preview-caption">Illustrative interface preview · Sample figures</span>
  </div>
}

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false)
  const closeMenu = () => setMenuOpen(false)

  return <main className="landing" id="top">
    <section className="landing-hero-shell">
      <header className="landing-header">
        <div className="landing-nav-wrap"><Brand />
          <button className="landing-menu-button" aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={21}/> : <Menu size={21}/>}</button>
          <nav className={`landing-nav${menuOpen ? ' is-open' : ''}`} aria-label="Main navigation">
            <a href="#features" onClick={closeMenu}>Features</a><a href="#workflow" onClick={closeMenu}>Workflow</a><a href="#benefits" onClick={closeMenu}>Benefits</a><a href="#faq" onClick={closeMenu}>FAQ</a>
            <a className="landing-nav-login" href={APP_LOGIN}>Sign in <ArrowUpRight size={14}/></a>
          </nav>
        </div>
      </header>

      <section className="landing-hero" aria-labelledby="hero-heading">
        <div className="hero-copy">
          <span className="hero-kicker"><i/> BUSINESS, IN CLEAR VIEW</span>
          <h1 id="hero-heading">Run your business.<br/><em>Not the busywork.</em></h1>
          <p className="hero-description">Manage sales, inventory, expenses, customers, and business performance from one streamlined POS platform built to keep your operations organized and your decisions informed.</p>
          <div className="hero-actions"><a className="button-primary" href={APP_LOGIN}>Access your POS <ArrowRight size={17}/></a><a className="button-secondary" href="#features">Explore features <ArrowDown size={16}/></a></div>
          <p className="hero-value-line"><Check size={15}/> Sales. Inventory. Expenses. Insights. <strong>All in one place.</strong></p>
        </div>
        <div className="hero-visual"><div className="hero-visual-glow"/><DashboardPreview/></div>
        <div className="hero-bottom-note"><span>MADE FOR THE DAY-TO-DAY</span><span>One workspace for your business operations <ArrowDown size={13}/></span></div>
      </section>
    </section>

    <section className="section features-section" id="features">
      <div className="section-heading"><span className="section-eyebrow">YOUR BUSINESS, CONNECTED</span><h2>Less switching.<br/><em>More clarity.</em></h2><p>Bring the essential parts of running a product-based business into one connected workspace.</p></div>
      <div className="feature-grid">{features.map(({ icon: Icon, title, text }, i) => <article className="feature-card" key={title}><div className="feature-icon"><Icon size={20}/></div><span className="feature-number">0{i + 1}</span><h3>{title}</h3><p>{text}</p><span className="feature-rule"/></article>)}</div>
    </section>

    <section className="workflow-section" id="workflow">
      <div className="section workflow-heading"><div><span className="section-eyebrow">A MORE CONNECTED DAY</span><h2>From first sale<br/>to daily close.</h2></div><p>Each part of the workday builds on the records you keep, so your team can move from checkout to review in one familiar place.</p></div>
      <div className="workflow-steps">{workflow.map(({ number, title, text }, i) => <article className="workflow-step" key={number}><div className="workflow-step-top"><span>{number}</span>{i < workflow.length - 1 && <i/>}</div><h3>{title}</h3><p>{text}</p></article>)}</div>
    </section>

    <section className="section benefits-section" id="benefits">
      <div className="benefits-copy"><span className="section-eyebrow">BUILT AROUND YOUR WORK</span><h2>Clarity for the<br/><em>everyday details.</em></h2><p>When daily business activity lives in one system, it becomes easier to find the information you need and keep useful records up to date.</p><a className="text-link" href={APP_LOGIN}>Explore the workspace <ArrowRight size={16}/></a></div>
      <div className="benefits-list">{benefits.map((benefit, i) => <div className="benefit-item" key={benefit}><span>0{i + 1}</span><p>{benefit}</p><Check size={17}/></div>)}</div>
    </section>

    <section className="product-section" id="preview">
      <div className="section product-layout"><div className="product-copy"><span className="section-eyebrow">A CLEARER VIEW OF THE DAY</span><h2>Your business,<br/><em>at a glance.</em></h2><p>See sales activity, transactions, stock status, and recent updates in a dashboard designed to help you find the important details quickly.</p><ul><li><Check size={15}/> Sales and transaction summaries</li><li><Check size={15}/> Inventory and low-stock visibility</li><li><Check size={15}/> Business reports and daily close</li></ul><a className="button-primary" href={APP_LOGIN}>Explore your POS <ArrowRight size={17}/></a></div><div className="product-preview-wrap"><DashboardPreview large/></div></div>
    </section>

    <section className="section audience-section"><div className="audience-heading"><span className="section-eyebrow">A PRACTICAL FIT</span><h2>For businesses that<br/><em>move products.</em></h2><p>Flexible tools for the people managing products, payments, and the details in between.</p></div><div className="audience-grid"><article><Store size={19}/><h3>Retail and general stores</h3><p>Keep checkout, products, and stock information close at hand.</p></article><article><PackageCheck size={19}/><h3>Product-based small businesses</h3><p>Connect incoming purchases with inventory and daily sales.</p></article><article><CreditCard size={19}/><h3>Shops tracking customer payments</h3><p>Keep customer records, payment history, and outstanding balances together.</p></article><article><ReceiptText size={19}/><h3>Teams reviewing business activity</h3><p>Bring sales, expenses, and reporting into a shared workflow.</p></article></div></section>

    <section className="faq-section" id="faq"><div className="section faq-layout"><div className="faq-heading"><span className="section-eyebrow">QUESTIONS, ANSWERED</span><h2>Good to<br/><em>know.</em></h2><p>Helpful details before you open your workspace.</p><a className="text-link" href={APP_LOGIN}>Go to sign in <ArrowRight size={16}/></a></div><div className="faq-list">{faqs.map(({ question, answer }) => <details key={question}><summary>{question}<span className="faq-chevron"><ChevronDown size={18}/></span></summary><p>{answer}</p></details>)}</div></div></section>

    <section className="closing-section"><div className="closing-orbit closing-orbit-one"/><div className="closing-orbit closing-orbit-two"/><div className="closing-content"><span className="section-eyebrow">YOUR WORKSPACE IS ONE CLICK AWAY</span><h2>Bring your business<br/>operations <em>into focus.</em></h2><p>Manage daily sales, records, and business activity from one organized workspace.</p><a className="button-primary closing-button" href={APP_LOGIN}>Open your POS <ArrowRight size={17}/></a></div></section>

    <footer className="landing-footer"><div className="section footer-main"><div className="footer-about"><Brand footer/><p>Sales, inventory, and business management in one considered workspace.</p><a className="agency-link" href="https://theorvion.io" target="_blank" rel="noreferrer">A product by The Orvion <ArrowUpRight size={13}/></a></div><div className="footer-links"><div><span>EXPLORE</span><a href="#features">Features</a><a href="#benefits">Benefits</a><a href="#workflow">Workflow</a><a href="#faq">FAQ</a></div><div><span>WORKSPACE</span><a href={APP_LOGIN}>Access POS <ArrowUpRight size={13}/></a><a href={`${APP_LOGIN.replace('/login', '/register')}`}>Create an account <ArrowUpRight size={13}/></a></div></div></div><div className="section footer-bottom"><span>© {new Date().getFullYear()} The Orvion. All rights reserved.</span><a href="#top">Back to top ↑</a><span>Thoughtfully built for business.</span></div></footer>
  </main>
}
