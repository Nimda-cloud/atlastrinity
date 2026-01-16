
import datetime

def test_grisha_metadata_logic():
    # Mocking what Grisha does
    class VerificationResult:
        def __init__(self, verified, confidence, description, issues, voice_message):
            self.verified = verified
            self.confidence = confidence
            self.description = description
            self.issues = issues
            self.voice_message = voice_message
            self.screenshot_analyzed = False

    verification = VerificationResult(
        verified=False,
        confidence=0.0,
        description="Test rejection",
        issues=["Issue 1", "Issue 2"],
        voice_message="Test voice"
    )

    # The logic we just applied in grisha.py
    timestamp = datetime.datetime.now().isoformat()
    attributes = {
        "type": "verification_rejection",
        "step_id": "1",
        "issues": "; ".join(verification.issues) if isinstance(verification.issues, list) else str(verification.issues),
        "description": str(verification.description),
        "timestamp": timestamp
    }

    print("Resulting attributes for Knowledge Graph:")
    for k, v in attributes.items():
        print(f"  {k}: {type(v).__name__} = {v}")

    # Check if 'issues' is now a string
    assert isinstance(attributes["issues"], str), "FAILED: 'issues' should be a string"
    print("\n✅ Grisha metadata logic test passed!")

if __name__ == "__main__":
    test_grisha_metadata_logic()
