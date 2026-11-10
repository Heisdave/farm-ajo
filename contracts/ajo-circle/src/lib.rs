//! Farm Ajo circle — NEAR **testnet** contract (v2: two-signature trust).
//!
//! Farmers save together so they can afford fertilizer before planting.
//!
//! One deployment of this contract is one Ajo (rotating savings) circle
//! aimed at a shared fertilizer target:
//!
//!   * `new` creates the circle with a savings target, a fixed per-member
//!     contribution amount, the member list, and two designated role
//!     accounts set at creation: a **supplier** account and a **QC
//!     verifier** account. They must be different accounts.
//!   * `contribute` records a member's contribution and the running pot.
//!     When the pot reaches the target the circle flips `open -> funded`.
//!   * `record_delivery` — callable ONLY by the designated supplier
//!     account, and only once the circle is funded — records what was
//!     delivered (bags, blend grade, total cost). Flips
//!     `funded -> delivered`.
//!   * `attest_quality` — callable ONLY by the designated QC verifier
//!     account, and only after a delivery exists — records the quality
//!     attestation: the named checks and pass/fail. If QC passed, the
//!     circle flips `delivered -> verified`, the final state. A failed
//!     attestation is stored but does NOT verify the circle.
//!
//! Why two signatures: anyone can write "quality verified". This
//! contract makes that claim cost something — it can only be made by a
//! named, accountable verifier account whose whole attestation history
//! is public, and the supplier can never sign it for itself (the
//! supplier cannot mark its own homework; the verifier cannot invent a
//! delivery). The circle is final only when BOTH signatures exist and
//! QC passed.
//!
//! Everything is public and readable back (`get_circle`, `get_member`,
//! `get_delivery`, `get_attestation`), so anyone — another farmer, a
//! cooperative, a judge — can verify what was saved, what was
//! delivered, and who attested the quality, without trusting the
//! agent's say-so.
//!
//! Demo-scope simplifications, stated honestly:
//!   * Contributions are recorded by member id (the demo's farmers are
//!     simulated off-chain by the agent). A production version would take
//!     the member from `predecessor_account_id` and accept real token
//!     transfers (ft_transfer_call) instead of bare amounts.
//!   * Amounts are plain integer demo units standing in for
//!     naira-denominated testnet credits; no real funds move here.
//!   * The role accounts are enforced by `predecessor_account_id`, which
//!     is exactly the production mechanism; in the demo both role
//!     accounts are testnet infrastructure accounts run for the demo.

use near_sdk::collections::Vector;
use near_sdk::{env, near, AccountId, PanicOnDefault};

// NOTE: borsh for this enum comes from the near macro (serializers=[borsh]),
// the same pattern as the structs below — hand-written borsh derives do not
// resolve against near-sdk 5.1.0's re-exported borsh on this toolchain
// (found the hard way; see BUILD_NOTES.md).
#[near(serializers = [borsh])]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum CircleState {
    Open,
    Funded,
    Delivered,
    Verified,
}

impl CircleState {
    pub fn as_str(&self) -> &'static str {
        match self {
            CircleState::Open => "open",
            CircleState::Funded => "funded",
            CircleState::Delivered => "delivered",
            CircleState::Verified => "verified",
        }
    }
}

#[near(serializers = [borsh, json])]
#[derive(Clone)]
pub struct Member {
    pub member_id: String,
    pub contributed: u128,
}

/// Signature 1 of 2: the designated supplier's delivery record.
#[near(serializers = [borsh, json])]
#[derive(Clone)]
pub struct Delivery {
    pub supplier_name: String,
    pub bags: u32,
    pub grade: String,
    pub total_cost: u128,
    pub notes: String,
    pub delivered_by: AccountId,
    pub timestamp: u64,
}

/// Signature 2 of 2: the designated QC verifier's quality attestation.
#[near(serializers = [borsh, json])]
#[derive(Clone)]
pub struct QualityAttestation {
    pub verifier_name: String,
    pub qc_passed: bool,
    pub checks: Vec<String>,
    pub notes: String,
    pub attested_by: AccountId,
    pub timestamp: u64,
}

#[near(serializers = [json])]
pub struct CircleView {
    pub name: String,
    pub target: u128,
    pub contribution_amount: u128,
    pub pot: u128,
    pub state: String,
    pub member_count: u64,
    pub supplier_account: AccountId,
    pub verifier_account: AccountId,
    pub delivery: Option<Delivery>,
    pub attestation: Option<QualityAttestation>,
}

#[near(contract_state)]
#[derive(PanicOnDefault)]
pub struct Contract {
    owner: AccountId,
    name: String,
    target: u128,
    contribution_amount: u128,
    pot: u128,
    state: CircleState,
    members: Vector<Member>,
    supplier_account: AccountId,
    verifier_account: AccountId,
    delivery: Option<Delivery>,
    attestation: Option<QualityAttestation>,
}

#[near]
impl Contract {
    /// Create a circle. `members` is the list of member ids; every member
    /// owes the same fixed `contribution_amount`, and the circle is funded
    /// when the pot reaches `target`. `supplier_account` and
    /// `verifier_account` are the two designated role accounts; they must
    /// differ, so no single account can both deliver and vouch.
    #[init]
    pub fn new(
        name: String,
        target: u128,
        contribution_amount: u128,
        members: Vec<String>,
        supplier_account: AccountId,
        verifier_account: AccountId,
    ) -> Self {
        assert!(!name.is_empty(), "circle name must not be empty");
        assert!(target > 0, "target must be positive");
        assert!(
            contribution_amount > 0,
            "contribution_amount must be positive"
        );
        assert!(!members.is_empty(), "circle needs at least one member");
        assert!(
            supplier_account != verifier_account,
            "supplier and verifier must be different accounts - the supplier cannot mark its own homework"
        );
        let mut list = Vector::new(b"m");
        for member_id in members {
            assert!(!member_id.is_empty(), "member id must not be empty");
            list.push(&Member {
                member_id,
                contributed: 0,
            });
        }
        Self {
            owner: env::predecessor_account_id(),
            name,
            target,
            contribution_amount,
            pot: 0,
            state: CircleState::Open,
            members: list,
            supplier_account,
            verifier_account,
            delivery: None,
            attestation: None,
        }
    }

    fn member_index(&self, member_id: &str) -> Option<u64> {
        let mut i = 0;
        while i < self.members.len() {
            if let Some(m) = self.members.get(i) {
                if m.member_id == member_id {
                    return Some(i);
                }
            }
            i += 1;
        }
        None
    }

    /// Record one member's contribution. Returns the new pot total.
    /// Flips the circle to `funded` when the pot reaches the target.
    pub fn contribute(&mut self, member: String, amount: u128) -> u128 {
        assert!(
            self.state == CircleState::Open,
            "circle is not open for contributions"
        );
        assert!(amount > 0, "contribution amount must be positive");
        let idx = self
            .member_index(&member)
            .unwrap_or_else(|| panic!("member is not in this circle"));
        let mut m = self.members.get(idx).unwrap();
        m.contributed += amount;
        self.members.replace(idx, &m);
        self.pot += amount;
        env::log_str(&format!(
            "Farm Ajo: {member} contributed {amount}; pot is now {} of {}",
            self.pot, self.target
        ));
        if self.pot >= self.target {
            self.state = CircleState::Funded;
            env::log_str("Farm Ajo: target reached - circle is funded");
        }
        self.pot
    }

    /// Signature 1 of 2: record the delivery. Callable ONLY by the
    /// designated supplier account, and only for a funded circle.
    /// Returns the stored delivery record.
    pub fn record_delivery(
        &mut self,
        supplier_name: String,
        bags: u32,
        grade: String,
        total_cost: u128,
        notes: String,
    ) -> Delivery {
        assert!(
            env::predecessor_account_id() == self.supplier_account,
            "only the designated supplier account can record the delivery"
        );
        assert!(
            self.state == CircleState::Funded,
            "circle is not funded yet - delivery cannot be recorded"
        );
        assert!(!supplier_name.is_empty(), "supplier_name must not be empty");
        assert!(bags > 0, "bags must be positive");
        assert!(!grade.is_empty(), "grade must not be empty");
        assert!(total_cost > 0, "total_cost must be positive");
        let delivery = Delivery {
            supplier_name,
            bags,
            grade,
            total_cost,
            notes,
            delivered_by: env::predecessor_account_id(),
            timestamp: env::block_timestamp(),
        };
        self.delivery = Some(delivery.clone());
        self.state = CircleState::Delivered;
        env::log_str("Farm Ajo: delivery recorded by the supplier");
        delivery
    }

    /// Signature 2 of 2: attest the quality of the delivery. Callable
    /// ONLY by the designated QC verifier account, and only after the
    /// supplier has recorded a delivery. If QC passed, the circle flips
    /// to its final `verified` state; if QC failed, the attestation is
    /// stored but the circle stays `delivered` (not verified) and the
    /// verifier may attest again after the problem is fixed.
    /// Returns the stored attestation.
    pub fn attest_quality(
        &mut self,
        verifier_name: String,
        qc_passed: bool,
        checks: Vec<String>,
        notes: String,
    ) -> QualityAttestation {
        assert!(
            env::predecessor_account_id() == self.verifier_account,
            "only the designated QC verifier account can attest quality"
        );
        assert!(
            self.state == CircleState::Delivered,
            "no delivery to attest yet - the supplier must record the delivery first"
        );
        assert!(!verifier_name.is_empty(), "verifier_name must not be empty");
        assert!(!checks.is_empty(), "checks must not be empty");
        let attestation = QualityAttestation {
            verifier_name,
            qc_passed,
            checks,
            notes,
            attested_by: env::predecessor_account_id(),
            timestamp: env::block_timestamp(),
        };
        self.attestation = Some(attestation.clone());
        if qc_passed {
            self.state = CircleState::Verified;
            env::log_str("Farm Ajo: quality attested PASSED - circle is verified");
        } else {
            env::log_str("Farm Ajo: quality attested FAILED - circle is NOT verified");
        }
        attestation
    }

    /// Whole-circle view in one call.
    pub fn get_circle(&self) -> CircleView {
        CircleView {
            name: self.name.clone(),
            target: self.target,
            contribution_amount: self.contribution_amount,
            pot: self.pot,
            state: self.state.as_str().to_string(),
            member_count: self.members.len(),
            supplier_account: self.supplier_account.clone(),
            verifier_account: self.verifier_account.clone(),
            delivery: self.delivery.clone(),
            attestation: self.attestation.clone(),
        }
    }

    pub fn get_state(&self) -> String {
        self.state.as_str().to_string()
    }

    pub fn get_pot(&self) -> u128 {
        self.pot
    }

    pub fn get_member(&self, member: String) -> Member {
        let idx = self
            .member_index(&member)
            .unwrap_or_else(|| panic!("member is not in this circle"));
        self.members.get(idx).unwrap()
    }

    pub fn get_delivery(&self) -> Option<Delivery> {
        self.delivery.clone()
    }

    pub fn get_attestation(&self) -> Option<QualityAttestation> {
        self.attestation.clone()
    }

    pub fn get_supplier_account(&self) -> AccountId {
        self.supplier_account.clone()
    }

    pub fn get_verifier_account(&self) -> AccountId {
        self.verifier_account.clone()
    }

    pub fn get_owner(&self) -> AccountId {
        self.owner.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use near_sdk::test_utils::{accounts, VMContextBuilder};
    use near_sdk::testing_env;

    fn set_predecessor(account: AccountId) {
        let mut builder = VMContextBuilder::new();
        builder.predecessor_account_id(account);
        testing_env!(builder.build());
    }

    fn owner() -> AccountId {
        accounts(0)
    }
    fn supplier() -> AccountId {
        accounts(1)
    }
    fn verifier() -> AccountId {
        accounts(2)
    }
    fn stranger() -> AccountId {
        accounts(3)
    }

    fn setup() -> Contract {
        set_predecessor(owner());
        Contract::new(
            "Test Circle".to_string(),
            300,
            100,
            vec![
                "amina".to_string(),
                "yusuf".to_string(),
                "emeka".to_string(),
            ],
            supplier(),
            verifier(),
        )
    }

    fn fund_fully(contract: &mut Contract) {
        set_predecessor(owner());
        contract.contribute("amina".to_string(), 100);
        contract.contribute("yusuf".to_string(), 100);
        contract.contribute("emeka".to_string(), 100);
    }

    fn deliver(contract: &mut Contract) {
        set_predecessor(supplier());
        contract.record_delivery(
            "Kaduna Agro Inputs Ltd (demo supplier)".to_string(),
            20,
            "NPK 15-15-15".to_string(),
            300,
            "20 bags delivered to the co-operative store".to_string(),
        );
    }

    fn checks() -> Vec<String> {
        vec![
            "bag count matches the purchase order".to_string(),
            "sample bags weigh within +/-2% of the nominal 50 kg".to_string(),
        ]
    }

    #[test]
    fn contributions_accumulate_per_member_and_in_pot() {
        let mut contract = setup();
        let pot = contract.contribute("amina".to_string(), 100);
        assert_eq!(pot, 100);
        let pot = contract.contribute("yusuf".to_string(), 60);
        assert_eq!(pot, 160);
        assert_eq!(contract.get_pot(), 160);
        assert_eq!(contract.get_member("amina".to_string()).contributed, 100);
        assert_eq!(contract.get_member("yusuf".to_string()).contributed, 60);
        assert_eq!(contract.get_member("emeka".to_string()).contributed, 0);
        assert_eq!(contract.get_state(), "open");
        assert_eq!(contract.get_circle().member_count, 3);
        assert_eq!(contract.get_supplier_account(), supplier());
        assert_eq!(contract.get_verifier_account(), verifier());
    }

    #[test]
    fn pot_reaching_target_flips_circle_to_funded() {
        let mut contract = setup();
        contract.contribute("amina".to_string(), 100);
        contract.contribute("yusuf".to_string(), 100);
        assert_eq!(contract.get_state(), "open");
        let pot = contract.contribute("emeka".to_string(), 100);
        assert_eq!(pot, 300);
        assert_eq!(contract.get_state(), "funded");
        assert_eq!(contract.get_circle().state, "funded");
    }

    #[test]
    fn two_signatures_reach_verified() {
        let mut contract = setup();
        fund_fully(&mut contract);
        deliver(&mut contract);
        // One signature is NOT the final state.
        assert_eq!(contract.get_state(), "delivered");
        let stored = contract.get_delivery().expect("delivery stored");
        assert_eq!(stored.bags, 20);
        assert_eq!(stored.delivered_by, supplier());
        assert!(contract.get_attestation().is_none());

        set_predecessor(verifier());
        let att = contract.attest_quality(
            "Fatima Sule, QC Verifier (demo)".to_string(),
            true,
            checks(),
            "all checks passed at delivery".to_string(),
        );
        assert!(att.qc_passed);
        assert_eq!(att.attested_by, verifier());
        // Both signatures + pass = final state.
        assert_eq!(contract.get_state(), "verified");
        let view = contract.get_circle();
        assert_eq!(view.state, "verified");
        assert!(view.delivery.is_some());
        assert!(view.attestation.is_some());
    }

    #[test]
    #[should_panic(expected = "only the designated QC verifier account can attest quality")]
    fn supplier_cannot_attest_quality() {
        let mut contract = setup();
        fund_fully(&mut contract);
        deliver(&mut contract);
        // The supplier tries to mark its own homework.
        set_predecessor(supplier());
        contract.attest_quality(
            "Supplier self-check".to_string(),
            true,
            checks(),
            "trust us".to_string(),
        );
    }

    #[test]
    #[should_panic(expected = "only the designated supplier account can record the delivery")]
    fn verifier_cannot_record_delivery() {
        let mut contract = setup();
        fund_fully(&mut contract);
        // The verifier tries to invent a delivery.
        set_predecessor(verifier());
        contract.record_delivery(
            "Invented supplier".to_string(),
            20,
            "NPK 15-15-15".to_string(),
            300,
            "made up".to_string(),
        );
    }

    #[test]
    #[should_panic(expected = "only the designated supplier account can record the delivery")]
    fn stranger_cannot_record_delivery() {
        let mut contract = setup();
        fund_fully(&mut contract);
        set_predecessor(stranger());
        contract.record_delivery(
            "Some supplier".to_string(),
            20,
            "NPK 15-15-15".to_string(),
            300,
            "not the designated supplier".to_string(),
        );
    }

    #[test]
    #[should_panic(expected = "no delivery to attest yet")]
    fn attestation_before_delivery_is_rejected() {
        let mut contract = setup();
        fund_fully(&mut contract);
        set_predecessor(verifier());
        contract.attest_quality(
            "Fatima Sule, QC Verifier (demo)".to_string(),
            true,
            checks(),
            "too early".to_string(),
        );
    }

    #[test]
    #[should_panic(expected = "circle is not funded yet")]
    fn delivery_before_funding_is_rejected() {
        let mut contract = setup();
        contract.contribute("amina".to_string(), 100);
        set_predecessor(supplier());
        contract.record_delivery(
            "Kaduna Agro Inputs Ltd (demo supplier)".to_string(),
            20,
            "NPK 15-15-15".to_string(),
            300,
            "too early".to_string(),
        );
    }

    #[test]
    fn failed_qc_does_not_verify() {
        let mut contract = setup();
        fund_fully(&mut contract);
        deliver(&mut contract);
        set_predecessor(verifier());
        let att = contract.attest_quality(
            "Fatima Sule, QC Verifier (demo)".to_string(),
            false,
            checks(),
            "two bags underweight - delivery disputed".to_string(),
        );
        assert!(!att.qc_passed);
        // Attestation is on record, but the circle is NOT final.
        assert_eq!(contract.get_state(), "delivered");
        assert!(contract.get_attestation().is_some());
    }

    #[test]
    #[should_panic(expected = "supplier and verifier must be different accounts")]
    fn same_account_for_both_roles_is_rejected() {
        set_predecessor(owner());
        Contract::new(
            "Bad Circle".to_string(),
            300,
            100,
            vec!["amina".to_string()],
            supplier(),
            supplier(),
        );
    }

    #[test]
    #[should_panic(expected = "contribution amount must be positive")]
    fn zero_contribution_is_rejected() {
        let mut contract = setup();
        contract.contribute("amina".to_string(), 0);
    }

    #[test]
    #[should_panic(expected = "member is not in this circle")]
    fn unknown_member_contribution_is_rejected() {
        let mut contract = setup();
        contract.contribute("stranger".to_string(), 50);
    }

    #[test]
    #[should_panic(expected = "circle is not open for contributions")]
    fn contribution_after_funding_is_rejected() {
        let mut contract = setup();
        fund_fully(&mut contract);
        contract.contribute("amina".to_string(), 10);
    }
}
