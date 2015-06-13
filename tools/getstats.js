// Last time updated at Sep 16, 2014, 08:32:23

// Latest file can be found here: https://cdn.webrtc-experiment.com/getStats.js

// Muaz Khan     - www.MuazKhan.com
// MIT License   - www.WebRTC-Experiment.com/licence
// Source Code   - https://github.com/muaz-khan/getStats

// ___________
// getStats.js

// an abstraction layer runs top over RTCPeerConnection.getStats API
// cross-browser compatible solution
// http://dev.w3.org/2011/webrtc/editor/webrtc.html#dom-peerconnection-getstats

/*
rtcPeerConnection.getStats(function(result) {
    result.connectionType.remote.ipAddress
    result.connectionType.remote.candidateType
    result.connectionType.transport
});
*/

(function () {
    var RTCPeerConnection = window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
    window.getStats = function (callback, interval) {
        var peer = this;

        if(arguments[0] instanceof RTCPeerConnection) {
            peer = arguments[0];
            callback = arguments[1];
            interval = arguments[2];
        }

        function parseIncomingAudioReport(report) {
            return {
                audioOutputLevel: report.audioOutputLevel, // "23"
                bytesReceived: report.bytesReceived, // "16983"
                captureStartNtpTimeMs: report.googCaptureStartNtpTimeMs, // "-1"
                codecName: report.googCodecName, // "opus"
                currentDelayMs: report.googCurrentDelayMs, // "100"
                decodingCNG: report.googDecodingCNG, // "0"
                decodingCTN: report.googDecodingCTN, // "356"
                decodingCTSG: report.googDecodingCTSG, // "0"
                decodingNormal: report.googDecodingNormal, // "356"
                decodingPLC: report.googDecodingPLC, // "0"
                decodingPLCCNG: report.googDecodingPLCCNG, // "0"
                expandRate: report.googExpandRate, // "0"
                jitterBufferMs: report.googJitterBufferMs, // "43"
                jitterReceived: report.googJitterReceived, // "0"
                preferredJitterBufferMs: report.googPreferredJitterBufferMs, // "20"
                trackId: report.googTrackId, // "431a02bf-8913-47a6-807c-882881ea6eb2"
                id: report.id, // "ssrc_2174837908_recv"
                packetsLost: report.packetsLost, // "0"
                packetsReceived: report.packetsReceived, // "179"
                // ssrc: report.ssrc, // "2174837908"
                // timestamp: report.timestamp, // Fri Jun 12 2015 15:23:27 GMT+0200 (CEST)
                // transportId: report.transportId, // "Channel-audio-1"
                // type: report.type, // "ssrc"
            };
        }

        function parseOutgoingAudioReport(report) {
            return {
                audioInputLevel: report.audioInputLevel, // "15"
                bytesSent: report.bytesSent, // "16505"
                codecName: report.googCodecName, // "opus"
                echoCancellationEchoDelayMedian: report.googEchoCancellationEchoDelayMedian, // "-12"
                echoCancellationEchoDelayStdDev: report.googEchoCancellationEchoDelayStdDev, // "0"
                echoCancellationQualityMin: report.googEchoCancellationQualityMin, // "-1"
                echoCancellationReturnLoss: report.googEchoCancellationReturnLoss, // "-100"
                echoCancellationReturnLossEnhancement: report.googEchoCancellationReturnLossEnhancement, // "-100"
                jitterReceived: report.googJitterReceived, // "-1"
                rtt: report.googRtt, // "-1"
                trackId: report.googTrackId, // "558be40c-82e7-4bb2-b20d-e2abcd3bc3ea"
                typingNoiseState: report.googTypingNoiseState, // "false"
                id: report.id, // "ssrc_3067768073_send"
                packetsLost: report.packetsLost, // "-1"
                packetsSent: report.packetsSent, // "180"
                // ssrc: report.ssrc, // "3067768073"
                // timestamp: report.timestamp, // Fri Jun 12 2015 15:23:27 GMT+0200 (CEST)
                // transportId: report.transportId, // "Channel-audio-1"
                // type: report.type, // "ssrc"
            };
        }

        function parseIncomingVideoReport(report) {
            return {
                bytesReceived: report.bytesReceived, // "74557"
                captureStartNtpTimeMs: report.googCaptureStartNtpTimeMs, // "3643104203674"
                currentDelayMs: report.googCurrentDelayMs, // "25"
                decodeMs: report.googDecodeMs, // "2"
                firsSent: report.googFirsSent, // "0"
                frameHeightReceived: report.googFrameHeightReceived, // "480"
                frameRateDecoded: report.googFrameRateDecoded, // "0"
                frameRateOutput: report.googFrameRateOutput, // "0"
                frameRateReceived: report.googFrameRateReceived, // "30"
                frameWidthReceived: report.googFrameWidthReceived, // "640"
                jitterBufferMs: report.googJitterBufferMs, // "11"
                maxDecodeMs: report.googMaxDecodeMs, // "4"
                minPlayoutDelayMs: report.googMinPlayoutDelayMs, // "0"
                nacksSent: report.googNacksSent, // "0"
                plisSent: report.googPlisSent, // "0"
                renderDelayMs: report.googRenderDelayMs, // "10"
                targetDelayMs: report.googTargetDelayMs, // "25"
                trackId: report.googTrackId, // "e2eaa689-2da2-43b3-96a0-3a3213d77716"
                id: report.id, // "ssrc_3102970513_recv"
                packetsLost: report.packetsLost, // "0"
                packetsReceived: report.packetsReceived, // "109"
                // ssrc: report.ssrc, // "3102970513"
                // timestamp: report.timestamp, // Fri Jun 12 2015 15:23:27 GMT+0200 (CEST)
                // transportId: report.transportId, // "Channel-audio-1"
                // type: report.type, // "ssrc"
            };
        }

        function parseOutgoingVideoReport(report) {
            return {
                bytesSent: report.bytesSent, // "106680"
                adaptationChanges: report.googAdaptationChanges, // "0"
                avgEncodeMs: report.googAvgEncodeMs, // "8"
                bandwidthLimitedResolution: report.googBandwidthLimitedResolution, // "false"
                captureJitterMs: report.googCaptureJitterMs, // "24"
                captureQueueDelayMsPerS: report.googCaptureQueueDelayMsPerS, // "0"
                codecName: report.googCodecName, // "VP8"
                cpuLimitedResolution: report.googCpuLimitedResolution, // "false"
                encodeUsagePercent: report.googEncodeUsagePercent, // "70"
                firsReceived: report.googFirsReceived, // "0"
                frameHeightInput: report.googFrameHeightInput, // "480"
                frameHeightSent: report.googFrameHeightSent, // "480"
                frameRateInput: report.googFrameRateInput, // "28"
                frameRateSent: report.googFrameRateSent, // "30"
                frameWidthInput: report.googFrameWidthInput, // "640"
                frameWidthSent: report.googFrameWidthSent, // "640"
                nacksReceived: report.googNacksReceived, // "0"
                plisReceived: report.googPlisReceived, // "0"
                rtt: report.googRtt, // "81"
                trackId: report.googTrackId, // "3b51fae2-d996-4e35-b240-f93818f96ff4"
                viewLimitedResolution: report.googViewLimitedResolution, // "false"
                id: report.id, // "ssrc_3480135701_send"
                packetsLost: report.packetsLost, // "0"
                packetsSent: report.packetsSent, // "131"
                // ssrc: report.ssrc, // "3480135701"
                // timestamp: report.timestamp, // Fri Jun 12 2015 15:15:28 GMT+0200 (CEST)
                // transportId: report.transportId, // "Channel-audio-1"
                // type: report.type, // "ssrc"
            };
        }

        function parseBandwidthEstimationReport(report) {
            return {
                googActualEncBitrate: report.googActualEncBitrate, // "247232"
                googAvailableReceiveBandwidth: report.googAvailableReceiveBandwidth, // "188220"
                googAvailableSendBandwidth: report.googAvailableSendBandwidth, // "381160"
                googBucketDelay: report.googBucketDelay, // "0"
                googRetransmitBitrate: report.googRetransmitBitrate, // "0"
                googTargetEncBitrate: report.googTargetEncBitrate, // "282882"
                googTransmitBitrate: report.googTransmitBitrate, // "333128"
                // id: report.id, // "bweforvideo"
                // timestamp: report.timestamp, // Fri Jun 12 2015 15:23:27 GMT+0200 (CEST)
                // type: report.type, // "VideoBwe"
            };
        }

        function parseConnectionReport(report) {
            return {
                local: {
                    candidateType: report.googLocalCandidateType,
                    ipAddress: report.googLocalAddress
                },
                remote: {
                    candidateType: report.googRemoteCandidateType,
                    ipAddress: report.googRemoteAddress
                },
                transport: report.googTransportType
            };
        }

        function getPrivateStats() {
            _getStats(function (reports) {
                var result = {
                    audio: {},
                    video: {},
                    results: reports,
                };

                for (var i = 0; i < reports.length; ++i) {
                    var report = reports[i],
                        isIncomingAudio = report.audioOutputLevel !== undefined,
                        isOutgoingAudio = report.audioInputLevel !== undefined,
                        isIncomingVideo = report.googFrameRateReceived !== undefined,
                        isOutgoingVideo = report.googFrameRateSent !== undefined,
                        isConnectionInUse = report.type == 'googCandidatePair' && report.googActiveConnection == 'true',
                        isBandwidthEstimation = report.type == 'VideoBwe';

                    if (isIncomingAudio) {
                        result.audio.incoming = parseIncomingAudioReport(report);
                    } else if (isOutgoingAudio) {
                        result.audio.outgoing = parseOutgoingAudioReport(report);
                    } else if (isIncomingVideo) {
                        result.video.incoming = parseIncomingVideoReport(report);
                    } else if (isOutgoingVideo) {
                        result.video.outgoing = parseOutgoingVideoReport(report);
                    } else if (isBandwidthEstimation) {
                        result.video.bandwidth = parseBandwidthEstimationReport(report);
                    } else if (isConnectionInUse) {
                        // report.googActiveConnection means either STUN or TURN is used.
                        result.connectionType = parseConnectionReport(report);
                    }
                }
                if (result.video.incoming.id !== undefined &&
                    result.video.outgoing.id !== undefined &&
                    result.audio.incoming.id !== undefined &&
                    result.audio.outgoing.id !== undefined) {
                    callback(result);
                } else {
                    console.log("Failed to find all properties of getStats results, try again...");
                    console.log(reports);
                }
            });
        }

        // a wrapper around getStats which hides the differences (where possible)
        // following code-snippet is taken from somewhere on the github
        function _getStats(cb) {
            // if !peer or peer.signalingState == 'closed' then return;

            if (!!navigator.mozGetUserMedia) {
                var mediaStreamTrack = peer.getLocalStreams()[0].getAudioTracks()[0];
                peer.getStats(mediaStreamTrack).then(function (res) {
                        console.log(JSON.stringify(res));
                        var items = [];
                        res.forEach(function (result) {
                            items.push(result);
                        });
                        cb(items);
                }, cb);
            } else {
                peer.getStats(function (res) {
                    var items = [];
                    res.result().forEach(function (result) {
                        var item = {};
                        result.names().forEach(function (name) {
                            item[name] = result.stat(name);
                        });
                        item.id = result.id;
                        item.type = result.type;
                        item.timestamp = result.timestamp;
                        items.push(item);
                    });
                    cb(items);
                });
            }
        };

        getPrivateStats();

    }
})();

var _printedIpMaps = 0;
function printStats() {
    var rtcmanager = angular.element(document.body).injector().get('RTCManager');
    var peerConnections = rtcmanager.getPeerConnections();

    for (var i = 0; i < peerConnections.length; i++) {
        var peerConnection = peerConnections[i];
        getStats(peerConnection, function (result) {
            if (_printedIpMaps < peerConnections.length && result.connectionType) {
                var trackId = null;
                $.each(result.results, function (key) {
                    var res = result.results[key];
                    if (res.googFrameRateReceived) {
                        trackId = res.googTrackId;
                        return false;
                    }
                });
                console.log(result);
                _printedIpMaps += 1;
            }
            if (result.video) {
                var report = {
                    timestamp: new Date().getTime(),
                    data: result,
                }
                $.ajax('https://collect.thusoy.com/collect', {
                    type: 'POST',
                    data: JSON.stringify(report),
                    contentType: "application/json",
                    error: function (jqxhr, status, errorThrown) {
                        console.log("Posting stats to collector failed: " + status + "; " + errorThrown);
                    }
                });
            } else {
                console.log(result);
            }
        });
    }
    setTimeout(printStats, 1000);
}


console.log("Starting stats collection in 5s");
setTimeout(printStats, 5000);
