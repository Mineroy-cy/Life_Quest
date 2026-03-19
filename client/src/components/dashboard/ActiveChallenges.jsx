import ChallengeCard from "../challenges/ChallengeCard";

export default function ActiveChallenges({ challenge }) {
  return (
    <section>
      <ChallengeCard challenge={challenge} />
    </section>
  );
}
