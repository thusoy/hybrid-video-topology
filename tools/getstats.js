// Last time updated at May 23, 2015, 08:32:23
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
getStats(function(result) {
    result.connectionType.remote.ipAddress
    result.connectionType.remote.candidateType
    result.connectionType.transport
});
*/
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
    RTCPeerConnection = window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
    window.getStats = function (callback, interval) {
        var peer = this;

        if(arguments[0] instanceof RTCPeerConnection) {
            peer = arguments[0];
            callback = arguments[1];
            interval = arguments[2];
        }

        var globalObject = {
            audio: {},
            video: {}
        };

        getPrivateStats();

        function getPrivateStats() {
            _getStats(function (results) {
                var result = {
                    audio: {},
                    video: {},
                    results: results,
                };

                for (var i = 0; i < results.length; ++i) {
                    var res = results[i];

                    if (res.googCodecName == 'opus' && res.googCurrentDelayMs) {
                        // Incoming audio
                        if (!globalObject.audio.prevBytesSent)
                            globalObject.audio.prevBytesSent = res.bytesSent;

                        var bytes = res.bytesSent - globalObject.audio.prevBytesSent;
                        globalObject.audio.prevBytesSent = res.bytesSent;

                        var kilobytes = bytes / 1024;

                        result.audio = merge(result.audio, {
                            availableBandwidth: kilobytes.toFixed(1),
                            inputLevel: res.audioInputLevel,
                            packetsLost: res.packetsLost,
                            rtt: res.googRtt,
                            packetsSent: res.packetsSent,
                            currentDelayMs: res.googCurrentDelayMs,
                            bytesSent: res.bytesSent
                        });
                    }
                    if (res.googFrameHeightReceived || res.googFrameRateReceived) {
                        result.video = merge(result.video, {
                            found: 1,
                            bytesReceived: res.bytesReceived,
                            captureStartNtpTimeMs: res.googCaptureStartNtpTimeMs,
                            currentDelayMs: res.googCurrentDelayMs,
                            decodeMs: res.googDecodeMs,
                            frameRateDecoded: res.googFrameRateDecoded,
                            frameRateOutput: res.googFrameRateOutput,
                            frameRateReceived: res.googFrameRateReceived,
                            jitterBufferMs: res.googJitterBufferMs,
                            maxDecodeMs: res.googMaxDecodeMs,
                            minPlayoutDelayMs: res.googMinPlayoutDelayMs,
                            nacksSent: res.googNacksSent,
                            renderDelayMs: res.googRenderDelayMs,
                            targetDelayMs: res.googTargetDelayMs,
                            packetsLost: res.packetsLost,
                            packetsReceived: res.packetsReceived,
                            transportId: res.transportId,
                        });
                    }

                    if (res.type == 'VideoBwe') {
                        result.video.bandwidth = {
                            googActualEncBitrate: res.googActualEncBitrate,
                            googAvailableSendBandwidth: res.googAvailableSendBandwidth,
                            googAvailableReceiveBandwidth: res.googAvailableReceiveBandwidth,
                            googRetransmitBitrate: res.googRetransmitBitrate,
                            googTargetEncBitrate: res.googTargetEncBitrate,
                            googBucketDelay: res.googBucketDelay,
                            googTransmitBitrate: res.googTransmitBitrate
                        };
                    }

                    // res.googActiveConnection means either STUN or TURN is used.

                    if (res.type == 'googCandidatePair' && res.googActiveConnection == 'true') {
                        result.connectionType = {
                            local: {
                                candidateType: res.googLocalCandidateType,
                                ipAddress: res.googLocalAddress
                            },
                            remote: {
                                candidateType: res.googRemoteCandidateType,
                                ipAddress: res.googRemoteAddress
                            },
                            transport: res.googTransportType
                        };
                    }
                }

                callback(result);
            });
        }

        // a wrapper around getStats which hides the differences (where possible)
        // following code-snippet is taken from somewhere on the github
        function _getStats(cb) {
            // if !peer or peer.signalingState == 'closed' then return;

            if (!!navigator.mozGetUserMedia) {
                peer.getStats(
                    function (res) {
                        var items = [];
                        res.forEach(function (result) {
                            items.push(result);
                        });
                        cb(items);
                    },
                    cb
                );
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
    }

    function merge(mergein, mergeto) {
        if (!mergein) mergein = {};
        if (!mergeto) return mergein;

        for (var item in mergeto) {
            mergein[item] = mergeto[item];
        }
        return mergein;
    }
})();

var _printedIpMaps = 0;
function printStats() {
    var rtcmanager = angular.element(document.body).injector().get('RTCManager');
    var peerConnections = rtcmanager.getPeerConnections();

    for (var i = 0; i < peerConnections.length; i++) {
        var peerConnection = peerConnections[i];
        getStats(peerConnection, function (result) {
            var rtt = result.audio.rtt,
                bw = result.video.availableBandwidth;
            if (_printedIpMaps < peerConnections.length && result.connectionType) {
                var trackId = null;
                $.each(result.results, function (key) {
                    var res = result.results[key];
                    if (res.googFrameRateReceived) {
                        trackId = res.googTrackId;
                        return false;
                    }
                });
                console.log(trackId + ': ' + result.connectionType.remote.ipAddress);
                _printedIpMaps += 1;
            }
            if (result.video.found) {
                var senderip =  result.connectionType.remote.ipAddress,
                    myip = result.connectionType.local.ipAddress;
                senderip = senderip.slice(0, senderip.indexOf(':'));
                myip = myip.slice(0, myip.indexOf(':'));
                var report = {
                    sender: senderip,
                    receiver: myip,
                    data: {
                        timestamp: new Date().getTime(),
                        rtt: rtt,
                        delayAudio: result.audio.currentDelayMs,
                        delayVideo: result.video.currentDelayMs,
                        audio: result.audio,
                        video: result.video,
                    }
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
