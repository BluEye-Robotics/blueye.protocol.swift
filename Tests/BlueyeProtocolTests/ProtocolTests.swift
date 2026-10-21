import BlueyeProtocol
import SwiftProtobuf
import XCTest

final class ProtocolTests: XCTestCase {
  func testAttitudeMatchesWireFixture() throws {
    let attitude = Blueye_Protocol_Attitude.with {
      $0.roll = 1
      $0.pitch = 2
      $0.yaw = 3
    }
    // The same fixed32 wire fixture is checked by the Kotlin client tests.
    let expected = Data([
      0x0d, 0x00, 0x00, 0x80, 0x3f,
      0x15, 0x00, 0x00, 0x00, 0x40,
      0x1d, 0x00, 0x00, 0x40, 0x40
    ])
    XCTAssertEqual(try attitude.serializedData(), expected)
    XCTAssertEqual(try Blueye_Protocol_Attitude(serializedBytes: expected), attitude)
  }

  func testAnyAndTimestampRoundTrip() throws {
    let attitude = Blueye_Protocol_Attitude.with { $0.yaw = 90 }
    var record = Blueye_Protocol_BinlogRecord()
    record.payload = try Google_Protobuf_Any(message: attitude)
    record.unixTimestamp = Google_Protobuf_Timestamp.with {
      $0.seconds = 1_700_000_000
      $0.nanos = 123_456_789
    }

    let decoded = try Blueye_Protocol_BinlogRecord(serializedBytes: record.serializedData())
    // Any can hold a typed message or serialized bytes internally; compare its
    // wire representation and unpacked value rather than the storage form.
    XCTAssertEqual(try decoded.serializedData(), try record.serializedData())
    XCTAssertEqual(decoded.unixTimestamp, record.unixTimestamp)
    XCTAssertEqual(decoded.payload.typeURL, "type.googleapis.com/blueye.protocol.Attitude")
    XCTAssertEqual(try Blueye_Protocol_Attitude(unpackingAny: decoded.payload), attitude)
  }

  func testMissionOneofRoundTrip() throws {
    let mission = Blueye_Protocol_Mission.with {
      $0.id = 42
      $0.name = "Inspection"
      $0.instructions = [Blueye_Protocol_Instruction.with {
        $0.id = 1
        $0.depthSetPointCommand = Blueye_Protocol_DepthSetPointCommand.with {
          $0.depthSetPoint.depth = 10
        }
      }]
    }
    let decoded = try Blueye_Protocol_Mission(serializedBytes: mission.serializedData())
    XCTAssertEqual(decoded, mission)
    guard case .depthSetPointCommand(let command) = decoded.instructions[0].command else {
      return XCTFail("Expected the depth set-point oneof case")
    }
    XCTAssertEqual(command.depthSetPoint.depth, 10)
  }

  func testUnknownFieldsSurviveRoundTrip() throws {
    // Field 100, varint 7: a field introduced by a newer firmware.
    let bytes = Data([0xa0, 0x06, 0x07])
    let attitude = try Blueye_Protocol_Attitude(serializedBytes: bytes)
    XCTAssertEqual(try attitude.serializedData(), bytes)
    XCTAssertThrowsError(try Blueye_Protocol_Attitude(serializedBytes: [UInt8(0x0d)]))
  }
}
